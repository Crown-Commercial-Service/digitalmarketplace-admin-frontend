from flask import render_template
from flask_login import login_required

from .. import main
from ..auth import role_required
from ... import data_api_client
from . import get_template_data


@main.route('/agreements/<framework_slug>', methods=['GET'])
@login_required
@role_required('admin-ccs-sourcing')
def list_agreements(framework_slug):
    framework = data_api_client.get_framework(framework_slug)['frameworks']
    supplier_frameworks = data_api_client.find_framework_suppliers(
        framework_slug, agreement_returned=True
    )['supplierFrameworks']

    return render_template(
        'view_agreements.html',
        framework=framework,
        supplier_frameworks=supplier_frameworks,
        **get_template_data()
    )
