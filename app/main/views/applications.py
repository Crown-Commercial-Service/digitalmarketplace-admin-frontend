from flask import render_template, request, flash, url_for, jsonify, request
from flask_login import login_required

from .. import main
from ... import data_api_client
from ..auth import role_required

from react.render import render_component


@main.route('/applications')
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


@main.route('/applications/preview/')
@main.route('/applications/preview/<int:id>')
def preview_application(id=None):
    application = data_api_client.get_application(id)

    props = dict(application)
    props['basename'] = url_for('.preview_application', id=id)
    props['form_options'] = {
        'action': url_for('.preview_application', id=id),
        'submit_url': url_for('.preview_application', id=id)
    }

    rendered_component = render_component('bundles/SellerRegistration/ApplicationPreviewWidget.js', props)

    return render_template(
        '_react.html',
        component=rendered_component
    )


@main.route('/applications/convert_to_seller', methods=['POST'])
def convert_to_seller():
    application_id = request.json['id']
    result = data_api_client.convert_application_to_supplier(application_id)
    return jsonify(result)
