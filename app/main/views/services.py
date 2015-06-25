from flask import render_template, request, redirect, url_for, flash, \
    current_app, session

from dmutils.apiclient import HTTPError
from dmutils.content_loader import YAMLLoader, ContentBuilder
from dmutils.presenters import Presenters
from dmutils.s3 import S3
from dmutils.validation import Validate

from ... import data_api_client
from .. import main
from . import get_template_data


existing_service_options = [
    "app/section_order.yml",
    "app/content/g6/",
    YAMLLoader()
]
presenters = Presenters()


@main.route('', methods=['GET'])
def index():
    return render_template("index.html", **get_template_data())


@main.route('/services', methods=['GET'])
def find():
    if request.args.get("service_id") is None:
        return render_template("index.html", **get_template_data()), 404
    return redirect(
        url_for(".view", service_id=request.args.get("service_id")))


@main.route('/services/<service_id>', methods=['GET'])
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

    content = ContentBuilder(*existing_service_options)
    content.filter(service_data)

    template_data = get_template_data({
        "sections": content.sections,
        "service_data": presenters.present_all(service_data, content),
        "service_id": service_id
    })
    return render_template("view_service.html", **template_data)


@main.route('/services/status/<string:service_id>', methods=['POST'])
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
            "Digital Marketplace admin user", "Status changed to '{0}'".format(
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
def edit(service_id, section):

    service_data = data_api_client.get_service(service_id)['services']

    content = ContentBuilder(*existing_service_options)
    content.filter(service_data)

    template_data = get_template_data({
        "section": content.get_section(section),
        "service_data": service_data,
    })
    return render_template("edit_section.html", **template_data)


@main.route('/services/<service_id>/edit/<section>', methods=['POST'])
def update(service_id, section):

    s3_uploader = S3(
        bucket_name=main.config['S3_DOCUMENT_BUCKET'],
    )

    service_data = data_api_client.get_service(service_id)['services']
    posted_data = dict(
        list(request.form.items()) + list(request.files.items())
    )

    content = ContentBuilder(*existing_service_options)
    content.filter(service_data)

    # Turn responses which have multiple parts into lists
    for key in request.form:
        item_as_list = request.form.getlist(key)
        list_types = ['list', 'checkboxes', 'pricing']
        if (
            key != 'csrf_token' and
            content.get_question(key)['type'] in list_types
        ):
            posted_data[key] = item_as_list

    posted_data.pop('csrf_token', None)
    form = Validate(content, service_data, posted_data,
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
                session['username'],
                "admin app")
        except HTTPError as e:
            return e.message

    if form.errors:
        service_data.update(form.dirty_data)
        return render_template("edit_section.html", **get_template_data({
            "section": content.get_section(section),
            "service_data": service_data,
            "service_id": service_id,
            "errors": form.errors
            }))
    else:
        return redirect(url_for(".view", service_id=service_id))
