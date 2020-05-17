from flask import render_template, request, jsonify, url_for, abort, current_app
from flask_login import login_required, current_user

from .. import main
from ... import data_api_client
from ..auth import role_required

from react.render import render_component


@main.route('/evidence-assessments/<int:evidence_id>', methods=['GET'])
@main.route('/evidence-assessments', methods=['GET'])
@login_required
@role_required('admin', 'assessor')
def evidence_assessments_review(evidence_id=None):
    SCHEME = request.environ['wsgi.url_scheme']
    if evidence_id:
        evidence = data_api_client.req.evidence(evidence_id).get()['evidence']
    else:
        evidence = data_api_client.req.evidence().get()['evidence']

    rendered_component = render_component(
        'bundles/ApplicationsAdmin/EvidenceAssessmentsAdminWidget.js',
        {
            'evidence': evidence if evidence else None,
            'meta': {'url_approve': url_for('main.evidence_assessments_approve', _external=True, _scheme=SCHEME),
                     'url_reject': url_for('main.evidence_assessments_reject', _external=True, _scheme=SCHEME),
                     'server_name': current_app.config['DM_MAIN_SERVER_NAME']}
        }
    )

    return render_template(
        '_react.html',
        component=rendered_component
    )


@main.route('/evidence-assessments/<int:evidence_id>/previous', methods=['GET'])
@login_required
@role_required('admin', 'assessor')
def evidence_assessments_review_previous(evidence_id=None):
    SCHEME = request.environ['wsgi.url_scheme']
    evidence = None
    if evidence_id:
        evidence = data_api_client.req.evidence(evidence_id).previous().get()['evidence']

    rendered_component = render_component(
        'bundles/ApplicationsAdmin/EvidenceAssessmentsAdminWidget.js',
        {
            'evidence': evidence if evidence else None,
            'meta': {'url_approve': url_for('main.evidence_assessments_approve', _external=True, _scheme=SCHEME),
                     'url_reject': url_for('main.evidence_assessments_reject', _external=True, _scheme=SCHEME)}
        }
    )

    return render_template(
        '_react.html',
        component=rendered_component
    )


@main.route('/evidence-assessments/approve', methods=['POST'])
@login_required
@role_required('admin', 'assessor')
def evidence_assessments_approve():
    id = request.get_json(force=True)['id']
    if not id:
        abort(400, 'Evidence id is missing')
    result = (
        data_api_client.req.evidence(id)
        .approve()
        .post({'actioned_by': current_user.id})
    )
    return jsonify(result)


@main.route('/evidence-assessments/reject', methods=['POST'])
@login_required
@role_required('admin', 'assessor')
def evidence_assessments_reject():
    request_data = request.get_json(force=True)
    if 'id' not in request_data:
        abort(400, 'Evidence id is missing')
    id = request_data['id']
    failed_criteria = request_data['failed_criteria']
    data = {
       'actioned_by': current_user.id, 'failed_criteria': failed_criteria if failed_criteria else None
    }
    if 'vfm' in request_data:
        data['vfm'] = request_data['vfm']
    result = (
        data_api_client.req.evidence(id)
        .reject()
        .post(data)
    )
    return jsonify(result)
