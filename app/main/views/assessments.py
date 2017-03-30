from flask import render_template
from flask_login import login_required

from .. import main
from ... import data_api_client
from ..auth import role_required

from react.render import render_component


@main.route('/assessments', methods=['GET'])
@login_required
@role_required('admin')
def assessments_review():
    assessments = data_api_client.req.assessments().get()['assessments']

    rendered_component = render_component(
        'bundles/ApplicationsAdmin/AssessmentsAdminWidget.js',
        {
            'assessments': assessments,
        }
    )

    return render_template(
        '_react.html',
        component=rendered_component
    )
