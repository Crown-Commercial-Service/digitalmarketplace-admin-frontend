from flask import render_template, request, flash, url_for, jsonify
from flask_login import login_required

from .. import main
from ... import data_api_client
from ..auth import role_required

from react.render import render_component


@main.route('/applications')
def start_seller_signup():

    applications = data_api_client.find_applications()['applications']

    rendered_component = render_component(
        'bundles/ApplicationsAdmin/ApplicationsAdminWidget.js',
        {
            'applications': applications,
            'meta': {
                'url_convert_to_seller': url_for('main.convert_to_seller', _external=True),
                'heading': 'List of Applications',
            }
        }
    )

    return render_template(
        '_react.html',
        component=rendered_component
    )


@main.route('/applications/convert_to_seller', methods=['POST'])
def convert_to_seller():
    application_id = request.json['id']
    result = data_api_client.convert_application_to_supplier(application_id)
    return jsonify(result)
