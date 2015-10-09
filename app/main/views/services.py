from flask import render_template, request, redirect, url_for, flash, \
    current_app, abort
from flask_login import login_required, current_user
from datetime import datetime

from dmutils.apiclient import HTTPError
from dmutils.validation import Validate
from dmutils.formats import DATETIME_FORMAT, format_service_price
from dmutils.documents import upload_service_documents
from dmutils.s3 import S3


from ... import data_api_client
from ... import content_loader
from .. import main
from . import get_template_data

from ..auth import role_required
from ..helpers.diff_tools import get_diffs_from_service_data, get_revision_dates


@main.route('', methods=['GET'])
@login_required
@role_required('admin', 'admin-ccs-category', 'admin-ccs-sourcing')
def index():
    return render_template("index.html", **get_template_data())


@main.route('/services', methods=['GET'])
@login_required
@role_required('admin', 'admin-ccs-category')
def find():
    if request.args.get("service_id") is None:
        return render_template("index.html", **get_template_data()), 404
    return redirect(
        url_for(".view", service_id=request.args.get("service_id")))


@main.route('/services/<service_id>', methods=['GET'])
@login_required
@role_required('admin', 'admin-ccs-category')
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

    service_data['priceString'] = format_service_price(service_data)
    content = content_loader.get_builder('g-cloud-6', 'edit_service_as_admin')

    template_data = get_template_data(
        sections=content,
        service_data=service_data,
        service_id=service_id
    )
    return render_template("view_service.html", **template_data)


@main.route('/services/status/<string:service_id>', methods=['POST'])
@login_required
@role_required('admin')
def update_service_status(service_id):
    frontend_status = request.form['service_status']

    translate_frontend_to_api = {
        'removed': 'disabled',
        'public': 'published',
        'private': 'enabled'
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


@main.route('/services/<service_id>/edit/<section>', methods=['GET'])
@login_required
@role_required('admin')
def edit(service_id, section):
    service_data = data_api_client.get_service(service_id)['services']

    content = content_loader.get_builder('g-cloud-6', 'edit_service_as_admin').filter(service_data)

    template_data = get_template_data(
        section=content.get_section(section),
        service_data=service_data
    )
    return render_template("edit_section.html", **template_data)


@main.route(
    '/services/compare/<old_archived_service_id>...<new_archived_service_id>',
    methods=['GET']
)
@login_required
@role_required('admin', 'admin-ccs-category')
def compare(old_archived_service_id, new_archived_service_id):

    def validate_archived_services(old_archived_service, new_archived_service):

        if old_archived_service.get('id', -1) \
                != new_archived_service.get('id', -2):
            return False

        old_updated_at = datetime.strptime(
            old_archived_service.get('updatedAt'), DATETIME_FORMAT)

        new_updated_at = datetime.strptime(
            new_archived_service.get('updatedAt'), DATETIME_FORMAT)

        if old_updated_at >= new_updated_at:
            return False

        return True

    try:
        service_data_revision_1 = data_api_client.get_archived_service(
            old_archived_service_id)['services']

        service_data_revision_2 = data_api_client.get_archived_service(
            new_archived_service_id)['services']

        # ids exist, ids match, dates are chronological
        if not validate_archived_services(
                service_data_revision_1, service_data_revision_2):
            raise ValueError

        service_data = data_api_client.get_service(
            service_data_revision_1['id'])['services']

    except (HTTPError, KeyError, ValueError):
        return abort(404)

    content = content_loader.get_builder('g-cloud-6', 'edit_service_as_admin').filter(service_data)

    # It's possible to have an empty array if none of the lines were changed.
    # TODO This possibility isn't actually handled.
    service_diffs = get_diffs_from_service_data(
        sections=content.sections,
        revision_1=service_data_revision_1,
        revision_2=service_data_revision_2,
        include_unchanged_lines_in_output=False
    )

    revision_dates = None if not service_diffs else \
        get_revision_dates(
            service_data_revision_1,
            service_data_revision_2
        )

    template_data = get_template_data(
        diffs=service_diffs,
        revision_dates=revision_dates,
        sections=content.sections,
        service_data=service_data
    )
    return render_template("compare_revisions.html", **template_data)


@main.route('/services/<service_id>/edit/<section_id>', methods=['POST'])
@login_required
@role_required('admin')
def update(service_id, section_id):
    service = data_api_client.get_service(service_id)
    if service is None:
        abort(404)
    service = service['services']

    content = content_loader.get_builder('g-cloud-6', 'edit_service_as_admin').filter(service)
    section = content.get_section(section_id)
    if section is None or not section.editable:
        abort(404)

    errors = None
    posted_data = section.get_data(request.form)

    uploaded_documents, document_errors = upload_service_documents(
        S3(current_app.config['DM_S3_DOCUMENT_BUCKET']),
        current_app.config['DM_DOCUMENTS_URL'],
        service, request.files, section)

    if document_errors:
        errors = section.get_error_messages(document_errors, service['lot'])
    else:
        posted_data.update(uploaded_documents)

    if not errors and section.has_changes_to_save(service, posted_data):
        try:
            data_api_client.update_service(
                service_id,
                posted_data,
                current_user.email_address)
        except HTTPError as e:
            errors = section.get_error_messages(e.message, service['lot'])

    if errors:
        if not posted_data.get('serviceName', None):
            posted_data['serviceName'] = service.get('serviceName', '')
        return render_template(
            "edit_section.html",
            **get_template_data(
                section=section,
                service_data=posted_data,
                service_id=service_id,
                errors=errors
            )
        ), 400

    return redirect(url_for(".view", service_id=service_id))
