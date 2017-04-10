from flask import render_template, request, jsonify, url_for
from flask_login import login_required

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
            'meta': {'url_approve': url_for('main.assessments_approve', _external=True, _scheme=SCHEME)}
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
        .domains(assessment['supplier_domain']['domain']['id']).assessed().post({})
    return jsonify(result)
