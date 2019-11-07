from flask import current_app, render_template, request, jsonify, url_for
from flask_login import login_required, current_user

from .. import main
from ... import data_api_client
from ..auth import role_required

from react.render import render_component


@main.route('/agency', methods=['GET'])
@login_required
@role_required('admin')
def get_agencies():
    SCHEME = request.environ['wsgi.url_scheme']
    rendered_component = render_component(
        'bundles/ApplicationsAdmin/AgenciesAdminWidget.js',
        {
            'meta': {
                'url_agency_data': url_for('main.get_agencies_data', _external=True, _scheme=SCHEME)
            }
        }
    )
    return render_template(
        '_react.html',
        component=rendered_component
    )


@main.route('/agency/data', methods=['GET'])
@login_required
@role_required('admin')
def get_agencies_data():
    agencies = data_api_client.req.admin().agency().get()
    return jsonify(agencies['agencies'])


@main.route('/agency/<int:agency_id>', methods=['GET'])
@login_required
@role_required('admin')
def get_agency(agency_id):
    SCHEME = request.environ['wsgi.url_scheme']
    agency = data_api_client.req.admin().agency(agency_id).get()

    rendered_component = render_component(
        'bundles/ApplicationsAdmin/AgenciesAdminWidget.js',
        {
            'agency': agency['agency'],
            'meta': {
                'url_save_agency': url_for('main.save_agency', agency_id=agency_id, _external=True, _scheme=SCHEME)
            }
        }
    )

    return render_template(
        '_react.html',
        component=rendered_component
    )


@main.route('/agency/<int:agency_id>', methods=['POST'])
@login_required
@role_required('admin')
def save_agency(agency_id):
    SCHEME = request.environ['wsgi.url_scheme']
    json_payload = request.get_json(force=True)
    agency = data_api_client.req.admin().agency(agency_id).put({
        "agency": json_payload,
        'update_details': {'updated_by': current_user.email_address}
    })

    return jsonify(agency['agency'])
