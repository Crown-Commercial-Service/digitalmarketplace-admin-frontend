from flask import render_template, request, redirect, url_for, flash, \
    current_app
from flask_login import login_required, current_user
from datetime import datetime

from dmutils.apiclient import HTTPError
from dmutils.presenters import Presenters
from dmutils.s3 import S3
from dmutils.validation import Validate
from dmutils.formats import DATETIME_FORMAT

from ... import data_api_client, DISPLAY_DATETIME_FORMAT
from ... import service_content
from .. import main
from . import get_template_data

from ..helpers.diff_tools import StringDiffTool, ListDiffTool

presenters = Presenters()


def make_diffs_from_service_data(
        sections_to_diff=None,
        sections=None,
        revision_1=None,
        revision_2=None,
        if_unchanged=False
):
    def is_string(value):
        return type(value).__name__ == 'str' \
            or type(value).__name__ == 'unicode'

    def is_list(value):
        return type(value).__name__ == 'list'

    diffs = []

    for section in sections:
        if section['name'] in sections_to_diff:
            for question in section['questions']:
                question_revision_1 = revision_1[question['id']]
                question_revision_2 = revision_2[question['id']]

                if is_string(question_revision_1) \
                        and is_string(question_revision_2):
                    diff = StringDiffTool(
                        question_revision_1, question_revision_2, if_unchanged)

                elif is_list(question_revision_1) \
                        and is_list(question_revision_2):
                    diff = ListDiffTool(
                        question_revision_1, question_revision_2, if_unchanged)

                else:
                    continue
                question_diff = diff.render_lines()

                # if arrays are empty, there are no changes for this question
                if question_diff['revision_1'] or question_diff['revision_2']:
                    diffs.append({
                        'section_name': section['name'],
                        'label': question['question'],
                        'revisions':
                            [val + question_diff['revision_2'][i]
                             for i, val
                             in enumerate(question_diff['revision_1'])]
                    })

    return diffs


def get_revision_dates(revision_1=None, revision_2=None):

    def get_revision_date(date_string):
        # Tuesday, 10 June 2015 at 14:00
        return datetime.strptime(
            date_string, DATETIME_FORMAT
        ).strftime(DISPLAY_DATETIME_FORMAT)

    return {
        'revision_1': get_revision_date(revision_1['updatedAt']),
        'revision_2': get_revision_date(revision_2['updatedAt'])
    }


@main.route('', methods=['GET'])
@login_required
def index():
    return render_template("index.html", **get_template_data())


@main.route('/services', methods=['GET'])
@login_required
def find():
    if request.args.get("service_id") is None:
        return render_template("index.html", **get_template_data()), 404
    return redirect(
        url_for(".view", service_id=request.args.get("service_id")))


@main.route('/services/<service_id>', methods=['GET'])
@login_required
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

    content = service_content.get_builder().filter(service_data)

    template_data = get_template_data(
        sections=content,
        service_data=presenters.present_all(service_data, service_content),
        service_id=service_id
    )
    return render_template("view_service.html", **template_data)


@main.route('/services/status/<string:service_id>', methods=['POST'])
@login_required
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
            current_user.email_address,
            "Status changed to '{0}'".format(
                backend_status))

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
def edit(service_id, section):
    service_data = data_api_client.get_service(service_id)['services']

    content = service_content.get_builder().filter(service_data)

    template_data = get_template_data(
        section=content.get_section(section),
        service_data=service_data
    )
    return render_template("edit_section.html", **template_data)


@main.route(
    '/services/compare/<old_archived_service_id>...<new_archived_service_id>',
    methods=['GET']
)
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
        flash({'compare_error': True}, 'error')
        return redirect(url_for('.index'))

    content = service_content.get_builder().filter(service_data)

    # It's possible to have an empty array if none of the lines were changed.
    # TODO This possibility isn't actually handled.
    service_diffs = make_diffs_from_service_data(
        sections_to_diff=['Description', 'Features and benefits'],
        sections=content.sections,
        revision_1=service_data_revision_1,
        revision_2=service_data_revision_2,
        if_unchanged=False
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


@main.route('/services/<service_id>/edit/<section>', methods=['POST'])
@login_required
def update(service_id, section):
    s3_uploader = S3(
        bucket_name=main.config['S3_DOCUMENT_BUCKET'],
    )

    service_data = data_api_client.get_service(service_id)['services']
    posted_data = dict(
        list(request.form.items()) + list(request.files.items())
    )

    content = service_content.get_builder().filter(service_data)

    # Turn responses which have multiple parts into lists
    for key in request.form:
        item_as_list = request.form.getlist(key)
        list_types = ['list', 'checkboxes', 'pricing']
        if (
            key != 'csrf_token' and
            service_content.get_question(key)['type'] in list_types
        ):
            posted_data[key] = item_as_list

    posted_data.pop('csrf_token', None)
    form = Validate(service_content, service_data, posted_data,
                    main.config['DOCUMENTS_URL'], s3_uploader)
    form.validate()

    update_data = {}
    for question_id in form.clean_data:
        if question_id not in form.errors:
            update_data[question_id] = form.clean_data[question_id]

    if update_data:
        try:
            data_api_client.update_service(
                service_data['id'],
                update_data,
                current_user.email_address,
                "admin app")
        except HTTPError as e:
            return e.message

    if form.errors:
        service_data.update(form.dirty_data)
        return render_template("edit_section.html", **get_template_data(
            section=content.get_section(section),
            service_data=service_data,
            service_id=service_id,
            errors=form.errors
        ))
    else:
        return redirect(url_for(".view", service_id=service_id))
