
from flask import render_template, request, Response
from flask_login import login_required
from flask import flash

from dmutils.forms import render_template_with_csrf

import unicodecsv
from .. import main
from ... import data_api_client
from ..auth import role_required
from .zendesk import _user_info


@main.route('/users', methods=['GET'])
@login_required
@role_required('admin')
def find_user_by_email_address():
    template = "view_users.html"
    users = None

    email_address = request.args.get("email_address", None)
    if email_address:
        users = data_api_client.get_user(email_address=email_address)

    if users:
        user, supplier = _user_info(email_address)
        return render_template_with_csrf(
            template,
            users=[users['users']],
            email_address=email_address,
            user=user, supplier=supplier
        )
    else:
        flash('no_users', 'error')
        return render_template_with_csrf(
            template,
            status_code=404,
            users=list(),
            email_address=None
        )


@main.route('/users/download', methods=['GET'])
@login_required
@role_required('admin')
def list_frameworks_with_users(errors=None):
    bad_statuses = ['coming', 'expired']
    frameworks = [framework for framework in data_api_client.find_frameworks()['frameworks']
                  if framework['status'] not in bad_statuses]
    framework_options = [{'value': framework['slug'], 'label': framework['name']} for framework
                         in sorted(frameworks, key=lambda framework: framework['name'])]

    return render_template(
        "download_users.html",
        framework_options=framework_options,
        errors=errors
    ), 200 if not errors else 400


@main.route('/users/download/<framework_slug>', methods=['GET'])
@login_required
@role_required('admin')
def download_users(framework_slug):
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

    def iter_csv(rows):

        class Line(object):
            def __init__(self):
                self._line = None

            def write(self, line):
                self._line = line

            def read(self):
                return self._line

        line = Line()
        writer = unicodecsv.writer(line)
        for row in rows:
            writer.writerow([row.get(header, '') for header in supplier_headers])
            yield line.read()

    return Response(
        iter_csv(supplier_rows),
        mimetype='text/csv',
        headers={
            "Content-Disposition": "attachment;filename=users-{}.csv".format(framework_slug),
            "Content-Type": "text/csv; header=present"
        }
    )
