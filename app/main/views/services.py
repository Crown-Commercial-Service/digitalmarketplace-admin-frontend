import os
from collections import OrderedDict
from itertools import chain, dropwhile, islice

from dmapiclient import HTTPError
from dmapiclient.audit import AuditTypes
from dmcontent.formats import format_service_price
from dmutils import s3  # this style of import so we only have to mock once
from dmutils.documents import upload_service_documents
from dmutils.flask import timed_render_template as render_template
from dmutils.forms.errors import govuk_errors
from flask import abort, current_app, flash, redirect, request, url_for
from flask_login import current_user

from .. import main
from ..auth import role_required
from ..forms import EditFrameworkStatusForm
from ..helpers.diff_tools import html_diff_tables_from_sections_iter
from ..helpers.frameworks import get_framework_or_404
from ... import content_loader
from ... import data_api_client


NO_SERVICE_MESSAGE = "Could not find a service with ID: {service_id}"
API_ERROR_MESSAGE = "Error trying to retrieve service with ID: {service_id}"
UPDATE_SERVICE_STATUS_ERROR_MESSAGE = "Error trying to update status of service: {error_message}"
BAD_SERVICE_STATUS_MESSAGE = "Not a valid status: {service_status}"
SERVICE_STATUS_UPDATED_MESSAGE = "Service status has been updated to: {service_status}"
SERVICE_PUBLISHED_MESSAGE = "You published ‘{service_name}’."

ALL_ADMIN_ROLES = [
    'admin',
    'admin-ccs-category',
    'admin-ccs-sourcing',
    'admin-framework-manager',
    'admin-manager',
    'admin-ccs-data-controller'
]


@main.route('', methods=['GET'])
@role_required(*ALL_ADMIN_ROLES)
def index():
    frameworks = data_api_client.find_frameworks()['frameworks']
    frameworks = [
        fw for fw in frameworks if not (fw['status'] == 'coming' or (
            fw['status'] == 'expired' and fw["family"] != 'digital-outcomes-and-specialists'
        ))
    ]
    frameworks = sorted(frameworks, key=lambda x: x['id'], reverse=True)
    return render_template("index.html", frameworks=frameworks)


@main.route('/frameworks', methods=['GET'])
@role_required(*ALL_ADMIN_ROLES)
def view_frameworks():
    if os.getenv("DM_ENVIRONMENT") == 'production':
        abort(404)  # This endpoint isn't safe in production.

    frameworks = data_api_client.find_frameworks()['frameworks']
    frameworks.sort(key=lambda x: (x['family'], x['id']), reverse=True)

    return render_template(
        "view_frameworks.html",
        frameworks=frameworks,
    )


@main.route('/frameworks/<framework_slug>/status', methods=['GET', 'POST'])
@role_required(*ALL_ADMIN_ROLES)
def change_framework_status(framework_slug):
    if os.getenv("DM_ENVIRONMENT") == 'production':
        abort(404)  # This endpoint isn't safe in production.

    framework = data_api_client.get_framework(framework_slug)['frameworks']

    if not framework:
        abort(404, "Framework not found")

    form = EditFrameworkStatusForm()

    if request.method == "POST":
        status = form.data.get('status')

        data_api_client.update_framework(framework_slug, {"status": status}, user=current_user.email_address)

        return redirect(url_for('.view_frameworks'))
    else:
        form.status.data = framework['status']

    return render_template(
        "change_framework_status.html",
        form=form,
        framework=framework,
    )


@main.route('/services', methods=['GET'])
@role_required('admin', 'admin-ccs-category', 'admin-framework-manager')
def find_service():
    if request.args.get("service_id") is None:
        return render_template("find_suppliers_and_services.html"), 404
    return redirect(
        url_for(".view_service", service_id=request.args.get("service_id")))


@main.route('/services/<service_id>', methods=['GET'])
@role_required('admin', 'admin-ccs-category', 'admin-framework-manager')
def view_service(service_id):
    try:
        service = data_api_client.get_service(service_id)
        if service is None:
            flash(NO_SERVICE_MESSAGE.format(service_id=service_id), 'error')
            return redirect(url_for('.search_suppliers_and_services'))
        service_data = service['services']
    except HTTPError:
        flash(API_ERROR_MESSAGE.format(service_id=service_id), 'error')
        return redirect(url_for('.search_suppliers_and_services'))

    framework = get_framework_or_404(
        data_api_client, service_data['frameworkSlug'], allowed_statuses=['live', 'expired']
    )

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
    sections = content_loader.get_manifest(
        service_data['frameworkSlug'],
        'edit_service_as_admin',
    ).filter(service_data, inplace_allowed=True).summary(service_data, inplace_allowed=True)

    return render_template(
        "view_service.html",
        framework=framework,
        sections=sections,
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

    # Only services on live frameworks should have their status changed.
    service = data_api_client.get_service(service_id)['services']
    # TODO remove `expired` from below. It's a temporary fix to allow access to DOS2 as it's expired.
    get_framework_or_404(data_api_client, service['frameworkSlug'], allowed_statuses=['live', 'expired'])

    frontend_status = request.form['service_status']

    translate_frontend_to_api = {
        'removed': 'disabled',
        'public': 'published',
    }

    if frontend_status in translate_frontend_to_api.keys():
        backend_status = translate_frontend_to_api[frontend_status]
    else:
        flash(BAD_SERVICE_STATUS_MESSAGE.format(service_status=frontend_status), 'error')
        return redirect(url_for('.view_service', service_id=service_id))

    try:
        data_api_client.update_service_status(
            service_id, backend_status,
            current_user.email_address)

    except HTTPError as e:
        flash(UPDATE_SERVICE_STATUS_ERROR_MESSAGE.format(error_message=e.message), 'error')
        return redirect(url_for('.view_service', service_id=service_id))

    message = "admin.status.updated: " \
              "Service ID %s updated to '%s'"
    current_app.logger.info(message, service_id, frontend_status)
    if frontend_status == 'public':
        flash(
            SERVICE_PUBLISHED_MESSAGE.format(
                service_name=service.get('serviceName') or service['frameworkName'] + ' - ' + service['lotName']
            )
        )
    else:
        flash(SERVICE_STATUS_UPDATED_MESSAGE.format(service_status=frontend_status))
    return redirect(url_for('.view_service', service_id=service_id))


@main.route('/services/<service_id>/edit/<section_id>', methods=['GET'])
@main.route('/services/<service_id>/edit/<section_id>/<question_slug>', methods=['GET'])
@role_required('admin-ccs-category')
def edit_service(service_id, section_id, question_slug=None):
    service_data = data_api_client.get_service(service_id)['services']

    # we don't actually need the framework here; using this to 404 if framework for the service is not live
    # TODO remove `expired` from below. It's a temporary fix to allow access to DOS2 as it's expired.

    get_framework_or_404(data_api_client, service_data['frameworkSlug'], allowed_statuses=['live', 'expired'])

    content = content_loader.get_manifest(
        service_data['frameworkSlug'],
        'edit_service_as_admin',
    ).filter(service_data, inplace_allowed=True)

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


@main.route('/services/<service_id>/edit/<section_id>', methods=['POST'])
@main.route('/services/<service_id>/edit/<section_id>/<question_slug>', methods=['POST'])
@role_required('admin-ccs-category')
def update_service(service_id, section_id, question_slug=None):
    service = data_api_client.get_service(service_id)
    if service is None:
        abort(404)
    service = service['services']

    # we don't actually need the framework here; using this to 404 if framework for the service is not live
    # TODO remove `expired` from below. It's a temporary fix to allow access to DOS2 as it's expired.
    get_framework_or_404(data_api_client, service['frameworkSlug'], allowed_statuses=['live', 'expired'])

    content = content_loader.get_manifest(
        service['frameworkSlug'],
        'edit_service_as_admin',
    ).filter(service, inplace_allowed=True)
    section = content.get_section(section_id)
    if question_slug is not None:
        # Overwrite section with single question section for 'question per page' editing.
        section = section.get_question_as_section(question_slug)
    if section is None or not section.editable:
        abort(404)

    errors = None
    posted_data = section.get_data(request.form)

    uploaded_documents, document_errors = upload_service_documents(
        s3.S3(current_app.config['DM_S3_DOCUMENT_BUCKET'], endpoint_url=current_app.config.get("DM_S3_ENDPOINT_URL")),
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
            errors=govuk_errors(errors),
        ), 400

    return redirect(url_for(".view_service", service_id=service_id))


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
        ).filter(service, inplace_allowed=True).sections

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
