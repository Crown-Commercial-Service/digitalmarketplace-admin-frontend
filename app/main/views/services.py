from collections import OrderedDict
from itertools import chain, dropwhile, islice

from dmapiclient import HTTPError
from dmapiclient.audit import AuditTypes
from dmcontent.formats import format_service_price
from dmutils import s3  # this style of import so we only have to mock once
from dmutils.documents import upload_service_documents
from flask import abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user

from .. import main
from ..auth import role_required
from ..helpers.diff_tools import html_diff_tables_from_sections_iter
from ... import content_loader
from ... import data_api_client


@main.route('', methods=['GET'])
@role_required('admin', 'admin-ccs-category', 'admin-ccs-sourcing', 'admin-manager')
def index():
    frameworks = data_api_client.find_frameworks()
    frameworks = [fw for fw in frameworks['frameworks'] if fw['status'] in ('standstill', 'live')]
    frameworks = sorted(frameworks, key=lambda x: x['id'], reverse=True)

    return render_template("index.html",
                           frameworks_for_countersigning=frameworks)


@main.route('/services', methods=['GET'])
@role_required('admin', 'admin-ccs-category')
def find():
    if request.args.get("service_id") is None:
        return render_template("index.html"), 404
    return redirect(
        url_for(".view", service_id=request.args.get("service_id")))


@main.route('/services/<service_id>', methods=['GET'])
@role_required('admin-ccs-category')
def view(service_id):
    try:
        service = data_api_client.get_service(service_id)
        if service is None:
            flash({'no_service': service_id}, 'error')
            return redirect(url_for('.index'))
        service_data = service['services']
    except HTTPError:
        flash({'api_error': service_id}, 'error')
        return redirect(url_for('.index'))

    removed_by = removed_at = None
    if service_data['status'] != 'published':
        most_recent_audit_events = data_api_client.find_audit_events(
            latest_first="true",
            object_id=service_id,
            object_type="services",
            audit_type=AuditTypes.update_service_status
        )
        if most_recent_audit_events.get('auditEvents'):
            removed_by = most_recent_audit_events['auditEvents'][0]['user']
            removed_at = most_recent_audit_events['auditEvents'][0]['createdAt']

    service_data['priceString'] = format_service_price(service_data)
    content = content_loader.get_manifest(service_data['frameworkSlug'], 'edit_service_as_admin').filter(service_data)

    return render_template(
        "view_service.html",
        sections=content.summary(service_data),
        service_data=service_data,
        service_id=service_id,
        removed_by=removed_by,
        removed_at=removed_at,
        remove=request.args.get('remove', None),
        publish=request.args.get('publish', None),
    )


@main.route('/services/status/<string:service_id>', methods=['POST'])
@role_required('admin-ccs-category')
def update_service_status(service_id):
    frontend_status = request.form['service_status']

    translate_frontend_to_api = {
        'removed': 'disabled',
        'public': 'published',
    }

    if frontend_status in translate_frontend_to_api.keys():
        backend_status = translate_frontend_to_api[frontend_status]
    else:
        flash({'bad_status': frontend_status}, 'error')
        return redirect(url_for('.view', service_id=service_id))

    try:
        data_api_client.update_service_status(
            service_id, backend_status,
            current_user.email_address)

    except HTTPError as e:
        flash({'status_error': e.message}, 'error')
        return redirect(url_for('.view', service_id=service_id))

    message = "admin.status.updated: " \
              "Service ID %s updated to '%s'"
    current_app.logger.info(message, service_id, frontend_status)
    flash({'status_updated': frontend_status})
    return redirect(url_for('.view', service_id=service_id))


@main.route('/services/<service_id>/edit/<section_id>', methods=['GET'])
@main.route('/services/<service_id>/edit/<section_id>/<question_slug>', methods=['GET'])
@role_required('admin-ccs-category')
def edit(service_id, section_id, question_slug=None):
    service_data = data_api_client.get_service(service_id)['services']

    content = content_loader.get_manifest(service_data['frameworkSlug'], 'edit_service_as_admin').filter(service_data)

    section = content.get_section(section_id)

    if question_slug is not None:
        # Overwrite section with single question section for 'question per page' editing.
        section = section.get_question_as_section(question_slug)
    if section is None or not section.editable:
        abort(404)
    # handle sections with assurance fields
    service_data = section.unformat_data(service_data)

    return render_template(
        "edit_section.html",
        section=section,
        service_data=service_data,
    )


@main.route('/services/<service_id>/updates', methods=['GET'])
@role_required('admin-ccs-category')
def service_updates(service_id):
    service_response = data_api_client.get_service(service_id)
    if service_response is None:
        abort(404)
    service = service_response['services']

    supplier = data_api_client.get_supplier(service["supplierId"])["suppliers"]

    common_request_kwargs = {
        "object_id": service_id,
        "object_type": "services",
        "audit_type": AuditTypes.update_service,
        "acknowledged": "false",
    }

    all_update_events = latest_update_events = oldest_update_events = None
    latest_update_events_response = data_api_client.find_audit_events(
        latest_first="true",
        **common_request_kwargs
    )
    latest_update_events = latest_update_events_response["auditEvents"]

    if latest_update_events_response["links"].get("next"):
        # we haven't got all update events for this object. fetch the oldest
        oldest_update_events_response = data_api_client.find_audit_events(
            latest_first="false",
            **common_request_kwargs
        )
        oldest_update_events = oldest_update_events_response["auditEvents"][::-1]

        # now we check to see if we're able to splice together the full list using these two responses. we'll know this
        # if we are able to find the last of latest_update_events in oldest_update_events. if we're not able to, we'll
        # have to leave all_update_events as None to signal that we don't have all the events
        if latest_update_events[-1]["id"] in (audit_event["id"] for audit_event in oldest_update_events):
            all_update_events = tuple(audit_event for audit_event in chain(
                latest_update_events,
                # being careful here to swallow the actual *matching* event using islice
                islice(dropwhile(lambda ae: ae["id"] != latest_update_events[-1]["id"], oldest_update_events), 1, None),
            ))
    else:
        all_update_events = oldest_update_events = latest_update_events

    # so now we should be in the position where, in all cases:
    # - all_update_events should contain all update events unless this is not possible using two requests, in which
    #   case it is set to None
    # - latest_update_events[0] and oldest_update_events[-1] should contain the latest and oldest update events
    #   respectively
    extra_context = {}
    if latest_update_events:
        archived_service_response = data_api_client.get_archived_service(
            oldest_update_events[-1]["data"]["oldArchivedServiceId"]
        )

        if archived_service_response is None:
            raise ValueError("referenced archived_service_id does not exist?")

        extra_context["archived_service"] = archived_service = archived_service_response["services"]

        # the edit_service_as_admin manifest should hopefully be a superset of all editable fields
        extra_context["sections"] = sections = content_loader.get_manifest(
            service['frameworkSlug'],
            'edit_service_as_admin',
        ).filter(service).sections

        extra_context["diffs"] = OrderedDict(
            (question_id, table_html,)
            for section_slug, question_id, table_html in html_diff_tables_from_sections_iter(
                sections=sections,
                revision_1=archived_service,
                revision_2=service,
                table_preamble_template="diff_table/_table_preamble.html",
            )
        )

    return render_template(
        "compare_revisions.html",
        service=service,
        supplier=supplier,
        all_update_events=all_update_events,
        latest_update_events=latest_update_events,
        oldest_update_events=oldest_update_events,
        # below number of users who made edits might not be reliable if over 2 default length pages
        # (100 edits per page at the time of writing) of unapproved edits per service were made
        min_number_of_users_who_made_edits=len(frozenset(audit_event["user"] for audit_event in chain(
            latest_update_events,
            oldest_update_events,
        ))),
        **extra_context
    )


@main.route('/services/<service_id>/edit/<section_id>', methods=['POST'])
@main.route('/services/<service_id>/edit/<section_id>/<question_slug>', methods=['POST'])
@role_required('admin-ccs-category')
def update(service_id, section_id, question_slug=None):
    service = data_api_client.get_service(service_id)
    if service is None:
        abort(404)
    service = service['services']

    content = content_loader.get_manifest(service['frameworkSlug'], 'edit_service_as_admin').filter(service)
    section = content.get_section(section_id)
    if question_slug is not None:
        # Overwrite section with single question section for 'question per page' editing.
        section = section.get_question_as_section(question_slug)
    if section is None or not section.editable:
        abort(404)

    errors = None
    posted_data = section.get_data(request.form)

    uploaded_documents, document_errors = upload_service_documents(
        s3.S3(current_app.config['DM_S3_DOCUMENT_BUCKET']),
        'documents',
        current_app.config['DM_ASSETS_URL'],
        service, request.files, section)

    if document_errors:
        errors = section.get_error_messages(document_errors)
    else:
        posted_data.update(uploaded_documents)

    if not errors and section.has_changes_to_save(service, posted_data):
        try:
            data_api_client.update_service(
                service_id,
                posted_data,
                current_user.email_address,
                user_role='admin',
            )
        except HTTPError as e:
            errors = section.get_error_messages(e.message)

    if errors:
        return render_template(
            "edit_section.html",
            section=section,
            service_data=section.unformat_data(dict(service, **posted_data)),
            service_id=service_id,
            errors=errors,
        ), 400

    return redirect(url_for(".view", service_id=service_id))
