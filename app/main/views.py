from flask import current_app, flash, render_template, request, redirect, \
    session, url_for
from flask.ext.wtf import Form
from dmutils.apiclient import HTTPError

from .. import data_api_client
from . import main
from dmutils.validation import Validate
from dmutils.content_loader import ContentLoader
from dmutils.presenters import Presenters
from dmutils.s3 import S3
from .helpers.auth import check_auth, is_authenticated


content = ContentLoader(
    "app/section_order.yml",
    "bower_components/digital-marketplace-ssp-content/g6/"
)
presenters = Presenters()


@main.route('', methods=['GET'])
def index():
    return render_template("index.html", **get_template_data())


@main.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'GET':
        return render_template("login.html", form=Form(), **get_template_data({
            "previous_responses": None,
            "logged_out": "logged_out" in request.args
        }))
    form = Form()
    if form.validate_on_submit() and check_auth(
        request.form['username'],
        request.form['password'],
        main.config['PASSWORD_HASH']
    ):
        session['username'] = request.form['username']
        return redirect(url_for('.index'))

    return render_template("login.html", form=Form(), **get_template_data({
        "error": "Could not log in",
        "previous_responses": request.form
    }))


@main.route('/logout', methods=['GET'])
def logout():
    session.pop('username', None)
    return redirect(url_for('.login', logged_out=''))


@main.route('/services', methods=['GET'])
def find():
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

    presented_service_data = {}
    for key, value in service_data.items():
        presented_service_data[key] = presenters.present(
            value, content.get_question(key)
        )

    template_data = get_template_data({
        "sections": content.sections,
        "service_data": presented_service_data,
        "service_id": service_id
    })
    return render_template("view_service.html", form=Form(), **template_data)


@main.route('/services/status/<string:service_id>', methods=['POST'])
def update_service_status(service_id):
    form = Form()
    if not form.validate_on_submit():
        flash({'status_error': 'Invalid CSRF token supplied'}, 'error')
        return redirect(url_for('.view', service_id=service_id))

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
    template_data = get_template_data({
        "section": content.get_section(section),
        "service_data": data_api_client.get_service(service_id)['services'],
    })
    return render_template("edit_section.html", form=Form(), **template_data)


@main.route('/services/<service_id>/edit/<section>', methods=['POST'])
def update(service_id, section):
    form = Form()
    if not form.validate_on_submit():
        flash({'update_fail': 'Invalid CSRF token supplied'}, 'error')
        template_data = get_template_data({
            "section": content.get_section(section),
            "service_data": data_api_client.get_service(service_id)
            ['services'],
        })
        return render_template("edit_section.html", form=Form(),
                               **template_data)

    s3_uploader = S3(
        bucket_name=main.config['S3_DOCUMENT_BUCKET'],
    )

    service_data = data_api_client.get_service(service_id)['services']
    posted_data = dict(
        list(request.form.items()) + list(request.files.items())
    )

    # Turn responses which have multiple parts into lists
    for key in request.form:
        item_as_list = request.form.getlist(key)
        list_types = ['list', 'checkboxes', 'pricing']
        if content.get_question(key)['type'] in list_types:
            posted_data[key] = item_as_list

    form = Validate(content, service_data, posted_data,
                    main.config['DOCUMENTS_URL'], s3_uploader)
    update = {}

    form.validate()

    for question_id in form.clean_data:
        if question_id not in form.errors:
            update[question_id] = form.clean_data[question_id]

    if update:
        try:
            data_api_client.update_service(
                service_data['id'],
                update,
                session['username'],
                "admin app")
        except HTTPError as e:
            return e.message

    if form.errors:
        service_data.update(form.dirty_data)
        return render_template("edit_section.html", form=Form(),
                               **get_template_data(
                                   {
                                       "section": content.get_section(section),
                                       "service_data": service_data,
                                       "service_id": service_id,
                                       "errors": form.errors
                                       }
                                   ))
    else:
        return redirect(url_for(".view", service_id=service_id))


def get_template_data(merged_with={}):
    template_data = dict(main.config['BASE_TEMPLATE_DATA'], **merged_with)
    template_data["authenticated"] = is_authenticated()
    return template_data
