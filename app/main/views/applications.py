from flask import render_template, request, flash, url_for, jsonify, request, current_app, abort, Response
from flask_login import login_required, current_user

from .. import main
from ... import data_api_client
from ..auth import role_required

from react.render import render_component
from dmutils.file import s3_download_file
from dmutils.email import send_email, generate_token, EmailError
import os
import mimetypes


@main.route('/applications', methods=['GET'])
@login_required
@role_required('admin')
def applications_review():
    applications = data_api_client.req.applications().status('submitted').get(
        params=dict(order_by='application.status desc, created_at desc')
    )['applications']

    return applications_list(applications)


@main.route('/applications/all', methods=['GET'])
@login_required
@role_required('admin')
def applications_review_all():
    return applications_list([])


def applications_list(applications):
    SCHEME = request.environ['wsgi.url_scheme']
    convert_url = url_for('main.convert_to_seller', _external=True, _scheme=SCHEME)
    reject_url = url_for('main.reject_application', _external=True, _scheme=SCHEME)
    revert_url = url_for('main.revert_application', _external=True, _scheme=SCHEME)
    preview_url = url_for('main.preview_application', _external=True, _scheme=SCHEME)
    search_url = url_for('main.search_applications', keyword='', _external=True, _scheme=SCHEME)
    delete_url = url_for('main.delete_application', id=0, _external=True, _scheme=SCHEME)
    edit_url = '{}://{}/{}/'.format(
        current_app.config['DM_HTTP_PROTO'],
        current_app.config['DM_MAIN_SERVER_NAME'],
        'sellers/application'
    )

    rendered_component = render_component(
        'bundles/ApplicationsAdmin/ApplicationsAdminWidget.js',
        {
            'applications': applications,
            'meta': {
                'url_convert_to_seller': convert_url,
                'url_reject_application': reject_url,
                'url_delete_application': delete_url,
                'url_revert_application': revert_url,
                'url_edit_application': edit_url,
                'url_preview': preview_url,
                'url_search_applications': search_url,
                'heading': 'Applications for approval',
            }
        }
    )

    return render_template(
        '_react.html',
        component=rendered_component
    )


@main.route('/applications/preview/', methods=['GET'])
@main.route('/applications/preview/<int:id>', methods=['GET'])
@login_required
@role_required('admin')
def preview_application(id=None):
    application = data_api_client.get_application(id)

    props = dict(application)
    props['basename'] = url_for('.preview_application', id=id)
    props['application']['documents_url'] = url_for('.download_single_file', id=id, slug='')
    props['application']['case_study_url'] = url_for('.preview_application_casestudy', application_id=id),
    props['form_options'] = {
        'action': url_for('.preview_application', id=id),
        'submit_url': url_for('.preview_application', id=id),

    }

    rendered_component = render_component('bundles/SellerRegistration/ApplicationPreviewWidget.js', props)

    return render_template(
        '_react.html',
        component=rendered_component
    )


@main.route('/applications/case-study/<int:application_id>/', methods=['GET'])
@main.route('/applications/case-study/<int:application_id>/<string:case_study_id>', methods=['GET'])
@login_required
@role_required('admin')
def preview_application_casestudy(application_id, case_study_id):
    application = data_api_client.get_application(application_id)
    for id in application.get('application', {}).get('case_studies', {}):
        if type(id) is dict:
            case_study = id
            id = case_study['id']
        else:
            case_study = application['application']['case_studies'][id]

        if str(id) == case_study_id:
            rendered_component = render_component('bundles/CaseStudy/CaseStudyViewWidget.js',
                                                  {"casestudy": case_study})

            return render_template(
                '_react.html',
                component=rendered_component
            )

    return abort(404, "Case study not found")


@main.route('/application/<int:id>/documents/<slug>', methods=['GET'])
@login_required
@role_required('admin')
def download_single_file(id, slug):
    file = s3_download_file(slug, os.path.join('applications', str(id)))

    mimetype = mimetypes.guess_type(slug)[0] or 'binary/octet-stream'
    return Response(file, mimetype=mimetype)


@main.route('/applications/<int:application_id>/update', methods=['POST'])
@login_required
@role_required('admin')
def update_application(application_id):
    json_payload = request.get_json(force=True)
    result = (data_api_client
              .req
              .applications(application_id)
              .admin()
              .put({"application": json_payload}))

    return jsonify(result)


@main.route('/applications/convert_to_seller', methods=['POST'])
@login_required
@role_required('admin')
def convert_to_seller():
    application_id = request.get_json(force=True)['id']
    result = data_api_client.req.applications(application_id).approve()\
        .post({'update_details': {'updated_by': current_user.email_address}})
    return jsonify(result)


@main.route('/applications/reject_application', methods=['POST'])
@login_required
@role_required('admin')
def reject_application():
    application_id = request.get_json(force=True)['id']
    result = data_api_client.req.applications(application_id).reject()\
        .post({'update_details': {'updated_by': current_user.email_address}})
    return jsonify(result)


@main.route('/applications/revert_application', methods=['POST'])
@login_required
@role_required('admin')
def revert_application():
    json_payload = request.get_json()
    application_id = json_payload.get('id')
    message = json_payload.get('msg', '')

    result = data_api_client.req.applications(application_id).revert() \
        .post({
            'update_details': {'updated_by': current_user.email_address},
            'message': message
        })
    return jsonify(result)


@main.route('/applications/search/<string:keyword>', methods=['GET'])
@login_required
@role_required('admin')
def search_applications(keyword):
    params = {'per_page': 1000}
    result = data_api_client.req.applications().search(keyword).get(params=params)
    return jsonify(result)


@main.route('/applications/<int:id>', methods=['DELETE'])
def delete_application(id):
    result = data_api_client.req.applications(id).delete({'updated_by': current_user.email_address})
    return jsonify(result)


@main.route('/applications/<int:id>/users', methods=['GET'])
@login_required
@role_required('admin')
def application_users(id):
    application = data_api_client.get_application(id)['application']
    users = data_api_client.req.users().get({'application_id': application['id']})['users']

    rendered_component = render_component(
        'bundles/ApplicationsAdmin/ApplicationsAdminWidget.js',
        {
            'users': users,
            'meta': {
                'application': application,
                'url_move_existing_user': url_for('.move_user_to_application', application_id=id),
                'url_invite_user': url_for('.invite_user_to_application', application_id=id),
            }
        }
    )

    return render_template(
        '_react.html',
        component=rendered_component
    )


@main.route('/applications/<int:id>/edit', methods=['GET'])
@login_required
@role_required('admin')
def application_edit(id):
    application = data_api_client.get_application(id)['application']

    if 'supplier' in application:
        del application['supplier']

    rendered_component = render_component(
        'bundles/ApplicationsAdmin/ApplicationsAdminWidget.js',
        {
            'application': application,
            'meta': {
                'url_app_update': url_for('.update_application', application_id=id),
            }
        }
    )

    return render_template(
        '_react.html',
        component=rendered_component
    )


@main.route('/applications/<int:application_id>/move-existing-user', methods=['POST'])
@login_required
@role_required('admin')
def move_user_to_application(application_id):
    json_payload = request.get_json(True)
    email_address = json_payload.get('email')

    application = data_api_client.get_application(application_id)
    if not application:
        return abort(404)

    user = data_api_client.get_user(email_address=email_address)

    result = data_api_client.req.users(user['users']['id']).post(
        data={
            'users': {
                'application_id': application_id,
            },
            "updated_by": current_user.email_address
        }
    )
    return jsonify(result)


@main.route('/applications/<int:application_id>/invite-user', methods=['POST'])
@login_required
@role_required('admin')
def invite_user_to_application(application_id):
    json_payload = request.get_json(True)
    email_address = json_payload.get('email')
    name = json_payload.get('name')

    application = data_api_client.get_application(application_id)
    if not application:
        return abort(404)

    user_json = data_api_client.get_user(email_address=email_address)

    if user_json:
        return abort(400)

    token_data = {'id': application_id, 'name': name, 'email_address': email_address}
    token = generate_token(token_data, current_app.config['SECRET_KEY'], current_app.config['INVITE_EMAIL_SALT'])

    url = '{}://{}/{}/{}'.format(
        current_app.config['DM_HTTP_PROTO'],
        current_app.config['DM_MAIN_SERVER_NAME'],
        current_app.config['CREATE_APPLICANT_PATH'],
        format(token)
    )

    email_body = render_template(
        'emails/invite_user_application_email.html',
        url=url,
        supplier=application['application']['name'],
        name=name,
    )

    try:
        send_email(
            email_address,
            email_body,
            current_app.config['INVITE_EMAIL_SUBJECT'],
            current_app.config['INVITE_EMAIL_FROM'],
            current_app.config['INVITE_EMAIL_NAME'],
        )
    except EmailError as e:
        current_app.logger.error(
            'Invitation email failed to send error {} to {} supplier {} supplier code {} '.format(
                str(e),
                email_address,
                current_user.supplier_name,
                current_user.supplier_code)
        )
        abort(503, "Failed to send user invite reset")

    return jsonify(success=True), 200
