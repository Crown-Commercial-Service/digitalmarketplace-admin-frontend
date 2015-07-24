from flask import render_template, request, redirect, url_for, abort
from flask_login import login_required

from .. import main
from . import get_template_data
from ... import data_api_client
from requests import HTTPError


@main.route('/suppliers/users', methods=['GET'])
@login_required
def find_supplier_users():

    if "supplier_id" not in request.args or len(request.args.get("supplier_id")) <= 0:
        return render_template("index.html", **get_template_data()), 404

    try:
        int(request.args.get("supplier_id"))
    except ValueError:
        abort(400, "invalid supplier id {}".format(request.args.get("supplier_id")))

    supplier = data_api_client.get_supplier(request.args.get("supplier_id"))
    if supplier is None:
        abort(404, "Supplier not found")
    users = data_api_client.find_users(request.args.get("supplier_id"))

    return render_template(
        "view_supplier_users.html",
        users=users["users"],
        supplier=supplier["suppliers"],
        **get_template_data()
    )


@main.route('/suppliers/users/<int:user_id>/unlock', methods=['POST'])
@login_required
def unlock_user(user_id):
    user = data_api_client.update_user(user_id, locked=False)
    return redirect(url_for('.find_supplier_users', supplier_id=user['users']['supplier']['supplierId']))


@main.route('/suppliers/users/<int:user_id>/activate', methods=['POST'])
@login_required
def activate_user(user_id):
    user = data_api_client.update_user(user_id, active=True)
    return redirect(url_for('.find_supplier_users', supplier_id=user['users']['supplier']['supplierId']))


@main.route('/suppliers/users/<int:user_id>/deactivate', methods=['POST'])
@login_required
def deactivate_user(user_id):
    user = data_api_client.update_user(user_id, active=False)
    return redirect(url_for('.find_supplier_users', supplier_id=user['users']['supplier']['supplierId']))


@main.route('/suppliers/services', methods=['GET'])
@login_required
def find_supplier_services():

    if "supplier_id" not in request.args or len(request.args.get("supplier_id")) <= 0:
        return render_template("index.html", **get_template_data()), 404

    try:
        int(request.args.get("supplier_id"))
    except ValueError:
        abort(400, "invalid supplier id {}".format(request.args.get("supplier_id")))

    supplier = data_api_client.get_supplier(request.args.get("supplier_id"))
    if supplier is None:
        abort(404, "Supplier not found")

    services = data_api_client.find_services(request.args.get("supplier_id"))

    return render_template(
        "view_supplier_services.html",
        services=services["services"],
        supplier=supplier["suppliers"],
        **get_template_data()
    )
