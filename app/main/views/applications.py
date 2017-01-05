from flask import render_template, request, flash, url_for, jsonify, request, current_app, abort
from flask_login import login_required

from .. import main
from ... import data_api_client
from ..auth import role_required

from react.render import render_component


@main.route('/applications', methods=['GET'])
@login_required
@role_required('admin')
def start_seller_signup():
    applications = data_api_client.find_applications()['applications']

    SCHEME = request.environ['wsgi.url_scheme']
    convert_url = url_for('main.convert_to_seller', _external=True, _scheme=SCHEME)
    preview_url = url_for('main.preview_application',  _external=True, _scheme=SCHEME)

    rendered_component = render_component(
        'bundles/ApplicationsAdmin/ApplicationsAdminWidget.js',
        {
            'applications': applications,
            'meta': {
                'url_convert_to_seller': convert_url,
                'url_preview': preview_url,
                'heading': 'List of Applications',
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

    app_documents_url = '{}://{}/sellers/application/{}/documents/'.format(
        current_app.config['DM_HTTP_PROTO'],
        current_app.config['DM_MAIN_SERVER_NAME'],
        id
    )

    props = dict(application)
    props['basename'] = url_for('.preview_application', id=id)
    props['application']['documents_url'] = app_documents_url
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


@main.route('/applications/convert_to_seller', methods=['POST'])
@login_required
@role_required('admin')
def convert_to_seller():
    application_id = request.get_json(force=True)['id']
    result = data_api_client.approve_application(application_id)
    return jsonify(result)
