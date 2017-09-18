from flask import current_app, render_template, request, jsonify, url_for
from flask_login import login_required, current_user

from .. import main
from ... import data_api_client
from ..auth import role_required

from react.render import render_component


@main.route('/assessments', methods=['GET'])
@login_required
@role_required('admin')
def assessments_review():
    SCHEME = request.environ['wsgi.url_scheme']
    assessments = data_api_client.req.assessments().get()['assessments']

    rendered_component = render_component(
        'bundles/ApplicationsAdmin/AssessmentsAdminWidget.js',
        {
            'assessments': assessments,
            'meta': {'url_approve': url_for('main.assessments_approve', _external=True, _scheme=SCHEME),
                     'url_reject': url_for('main.assessments_reject', _external=True, _scheme=SCHEME)}
        }
    )

    return render_template(
        '_react.html',
        component=rendered_component
    )


@main.route('/assessments/approve', methods=['POST'])
@login_required
@role_required('admin')
def assessments_approve():
    id = request.get_json(force=True)['id']
    assessment = data_api_client.req.assessments(id).get()
    result = data_api_client.req.suppliers(assessment['supplier_domain']['supplier']['id']) \
        .domains(assessment['supplier_domain']['domain']['id']).assessed()\
        .post({'update_details': {'updated_by': current_user.email_address}})
    return jsonify(result)


@main.route('/assessments/reject', methods=['POST'])
@login_required
@role_required('admin')
def assessments_reject():
    json_payload = request.get_json(force=True)
    application_id = json_payload.get('application_id')
    message = json_payload.get('message', '')

    assessment = data_api_client.req.assessments(application_id).reject() \
        .post({
            'update_details': {'updated_by': current_user.email_address},
            'message': message
        })
    return jsonify(assessment)


@main.route('/assessments/supplier', methods=['GET'])
@main.route('/assessments/supplier/<int:id>', methods=['GET'])
@login_required
@role_required('admin')
def assessments_supplier(id=None):
    application = {'application': data_api_client.get_supplier(id)['supplier']}

    props = dict(application)
    props['basename'] = url_for('.assessments_supplier', id=id)
    props['application']['documents_url'] = url_for('.download_single_file', id=id, slug='')
    props['application']['case_study_url'] = '{}://{}/{}/'.format(
        current_app.config['DM_HTTP_PROTO'],
        current_app.config['DM_MAIN_SERVER_NAME'],
        'case-study'
    )
    props['form_options'] = {
        'action': url_for('.preview_application', id=id),
        'submit_url': url_for('.preview_application', id=id),
    }

    rendered_component = render_component('bundles/SellerRegistration/ApplicationPreviewWidget.js', props)

    return render_template(
        '_react.html',
        component=rendered_component
    )
