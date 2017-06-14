from flask import render_template, request, flash, url_for, jsonify, request, current_app, abort, Response
from flask_login import login_required, current_user

from .. import main
from ... import data_api_client
from ..auth import role_required

from react.render import render_component
from dmutils.file import s3_download_file
import os
import mimetypes


@main.route('/applications', methods=['GET'])
@login_required
@role_required('admin')
def applications_review():
    return applications_list(status='submitted')


@main.route('/applications/all', methods=['GET'])
@login_required
@role_required('admin')
def applications_review_all():
    return applications_list()


def applications_list(status=None):
    if status:
        applications = data_api_client.req.applications().status(status).get(
            params=dict(order_by='application.status desc, created_at desc')
        )['applications']
    else:
        applications = data_api_client.req.applications().get(
            params=dict(order_by='application.status desc, created_at desc')
        )['applications']

    SCHEME = request.environ['wsgi.url_scheme']
    convert_url = url_for('main.convert_to_seller', _external=True, _scheme=SCHEME)
    reject_url = url_for('main.reject_application', _external=True, _scheme=SCHEME)
    revert_url = url_for('main.revert_application', _external=True, _scheme=SCHEME)
    preview_url = url_for('main.preview_application',  _external=True, _scheme=SCHEME)
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
                'url_revert_application': revert_url,
                'url_edit_application': edit_url,
                'url_preview': preview_url,
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

        if id == case_study_id:
            rendered_component = render_component('bundles/CaseStudy/CaseStudyViewWidget.js',
                                                  {"casestudy": application['application']['case_studies'][id]})

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
