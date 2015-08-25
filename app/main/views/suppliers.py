from flask import render_template, request, redirect, url_for, abort, current_app
from flask_login import login_required, current_user, flash

from .. import main
from . import get_template_data
from ... import data_api_client
from ..forms import EmailAddressForm
from dmutils.apiclient.errors import HTTPError
from dmutils.audit import AuditTypes
from dmutils.email import send_email, \
    generate_token, MandrillException


@main.route('/suppliers', methods=['GET'])
@login_required
def find_suppliers():
    suppliers = data_api_client.find_suppliers(prefix=request.args.get("supplier_name_prefix"))

    return render_template(
        "view_suppliers.html",
        suppliers=suppliers['suppliers'],
        **get_template_data()
    )


@main.route('/suppliers/users', methods=['GET'])
@login_required
def find_supplier_users():
    form = EmailAddressForm()

    supplier = get_supplier()
    users = data_api_client.find_users(request.args.get("supplier_id"))

    return render_template(
        "view_supplier_users.html",
        users=users["users"],
        form=form,
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

    supplier = get_supplier()
    services = data_api_client.find_services(request.args.get("supplier_id"))

    return render_template(
        "view_supplier_services.html",
        services=services["services"],
        supplier=supplier["suppliers"],
        **get_template_data()
    )


@main.route('/suppliers/<int:supplier_id>/invite-user', methods=['POST'])
@login_required
def invite_user(supplier_id):
    form = EmailAddressForm()

    try:
        suppliers = data_api_client.get_supplier(supplier_id)
        users = data_api_client.find_users(supplier_id)
    except HTTPError as e:
        current_app.logger.error(str(e), supplier_id)
        if e.status_code != 404:
            raise
        else:
            abort(404, "Supplier not found")

    if form.validate_on_submit():
        token = generate_token(
            {
                "supplier_id": supplier_id,
                "supplier_name": suppliers['suppliers']['name'],
                "email_address": form.email_address.data
            },
            current_app.config['SHARED_EMAIL_KEY'],
            current_app.config['INVITE_EMAIL_SALT']
        )

        url = "{}{}/{}".format(
            request.url_root,
            current_app.config['CREATE_USER_PATH'],
            format(token)
        )

        email_body = render_template(
            "emails/invite_user_email.html",
            url=url,
            supplier=suppliers['suppliers']['name'])

        try:
            send_email(
                form.email_address.data,
                email_body,
                current_app.config['DM_MANDRILL_API_KEY'],
                current_app.config['INVITE_EMAIL_SUBJECT'],
                current_app.config['INVITE_EMAIL_FROM'],
                current_app.config['INVITE_EMAIL_NAME'],
                ["user-invite"]
            )
        except MandrillException as e:
            current_app.logger.error(
                "Invitation email failed to send error {} to {} supplier {} supplier id {} ".format(
                    str(e),
                    form.email_address.data,
                    current_user.supplier_name,
                    current_user.supplier_id)
            )
            abort(503, "Failed to send user invite reset")

        data_api_client.create_audit_event(
            audit_type=AuditTypes.invite_user,
            user=current_user.email_address,
            object_type='suppliers',
            object_id=supplier_id,
            data={'invitedEmail': form.email_address.data})

        flash('user_invited', 'success')
        return redirect(url_for('.find_supplier_users', supplier_id=supplier_id))
    else:
        return render_template(
            "view_supplier_users.html",
            form=form,
            users=users["users"],
            supplier=suppliers["suppliers"],
            **get_template_data()
        ), 400


def get_supplier():

    if "supplier_id" not in request.args or len(request.args.get("supplier_id")) <= 0:
        abort(404, "Supplier not found")

    try:
        int(request.args.get("supplier_id"))
    except ValueError:
        abort(400, "invalid supplier id {}".format(request.args.get("supplier_id")))

    try:
        return data_api_client.get_supplier(request.args.get("supplier_id"))
    except HTTPError as e:
        if e.status_code != 404:
            raise
        else:
            abort(404, "Supplier not found")
