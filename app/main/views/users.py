from flask import render_template, request
from flask_login import login_required, current_user, flash

from .. import main
from . import get_template_data
from ... import data_api_client
from ..auth import role_required


@main.route('/users', methods=['GET'])
@login_required
@role_required('admin', 'admin-ccs-category')
def find_user_by_email_address():
    template = "view_users.html"
    users = None

    email_address = request.args.get("email_address", None)
    if email_address:
        users = data_api_client.get_user(email_address=request.args.get("email_address"))

    if users:
        return render_template(
            template,
            users=[users['users']],
            email_address=request.args.get("email_address"),
            **get_template_data())
    else:
        flash('no_users', 'error')
        return render_template(
            template,
            users=list(),
            email_address=None,
            **get_template_data()), 404
