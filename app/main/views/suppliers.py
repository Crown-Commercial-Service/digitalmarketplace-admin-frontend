from flask import render_template, request
from flask_login import login_required

from .. import main
from . import get_template_data
from ... import data_api_client


@main.route('/suppliers/users', methods=['GET'])
@login_required
def find_supplier_users():

    if "supplier_id" not in request.args or len(request.args.get("supplier_id")) <= 0:
        return render_template("index.html", **get_template_data()), 404

    supplier = data_api_client.get_supplier(request.args.get("supplier_id"))
    users = data_api_client.find_users(request.args.get("supplier_id"))

    return render_template(
        "view_supplier_users.html",
        users=users["users"],
        supplier=supplier["suppliers"],
        **get_template_data()
    )


@main.route('/suppliers/services', methods=['GET'])
@login_required
def find_supplier_services():

    if "supplier_id" not in request.args or len(request.args.get("supplier_id")) <= 0:
        return render_template("index.html", **get_template_data()), 404

    supplier = data_api_client.get_supplier(request.args.get("supplier_id"))
    services = data_api_client.find_services(request.args.get("supplier_id"))

    return render_template(
        "view_supplier_services.html",
        services=services["services"],
        supplier=supplier["suppliers"],
        **get_template_data()
    )
