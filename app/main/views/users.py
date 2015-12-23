from flask import render_template, request, Response
from flask_login import login_required, flash

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


@main.route('/users/export', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def export_users():
    bad_statuses = ['coming', 'expired']
    frameworks = [f for f in data_api_client.find_frameworks()['frameworks'] if f['status'] not in bad_statuses]
    # if frameworks is empty, framework options will be empty
    framework_options = [{'value': f['slug'], 'label': f['name']} for f in sorted(frameworks, key=lambda f: f['name'])]
    errors = []

    if framework_options and request.method == 'POST':

        framework_slug = request.form.get('framework_slug')
        if not framework_slug or framework_slug not in [f['slug'] for f in frameworks]:
            errors = [{
                "input_name": "framework_slug",
                "question": "Please select a framework"
            }]

        else:
            supplier_rows = data_api_client.export_users(framework_slug).get('users', [])
            supplier_headers = [
                "user_email",
                "user_name",
                "supplier_id",
                "declaration_status",
                "application_status",
                "application_result",
                "framework_agreement"
            ]
            # insert header column
            supplier_rows.insert(0, {header: header for header in supplier_headers})

            def generate():
                for row in supplier_rows:
                    row = ["{}".format(row.get(header, '')) for header in supplier_headers]
                    yield '{}{}'.format(','.join(row), '\r\n')

            return Response(
                generate(),
                mimetype='text/csv',
                headers={
                    "Content-Disposition": "attachment;filename=users-{}.csv".format(framework_slug),
                    "Content-Type": "text/csv; header=present"
                }
            )

    return render_template(
        "export.html",
        framework_options=framework_options,
        errors=errors,
        **get_template_data()
    ), 200 if not errors else 400
