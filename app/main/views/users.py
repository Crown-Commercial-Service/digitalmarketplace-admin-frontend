from __future__ import unicode_literals
from flask import render_template, request, Response
from flask_login import login_required, flash
from datetime import datetime
from dmutils import csv_generator

from .. import main
from ... import data_api_client
from ..auth import role_required


@main.route('/users', methods=['GET'])
@login_required
@role_required('admin')
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
            email_address=request.args.get("email_address")
        )
    else:
        flash('no_users', 'error')
        return render_template(
            template,
            users=list(),
            email_address=None
        ), 404


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

    formated_rows = []
    for row in supplier_rows:
        formated_rows.append([row[heading] for heading in supplier_headers])
    formated_rows.insert(0, supplier_headers)

    return Response(
        csv_generator.iter_csv(formated_rows),
        mimetype='text/csv',
        headers={
            "Content-Disposition": "attachment;filename=users-{}.csv".format(framework_slug),
            "Content-Type": "text/csv; header=present"
        }
    )


@main.route('/users/download/buyers', methods=['GET'])
@login_required
@role_required('admin')
def download_buyers_and_briefs():
    buyers = (user for user in data_api_client.find_users_iter(role='buyer'))
    briefs = (brief for brief in data_api_client.find_briefs_iter(with_users=True))
    buyer_headings = [
        "name",
        "emailAddress",
        "phoneNumber",
        "createdAt",
        "briefs"
    ]

    buyers_dict = {}
    for buyer in buyers:
        buyer['briefs'] = []
        buyers_dict[buyer['id']] = buyer

    for brief in briefs:
        for user in brief['users']:
            brief_string = '{} - {}'.format(brief['title'], 'open' if brief['status'] == 'live' else brief['status'])
            buyers_dict[user['id']]['briefs'].append(brief_string)

    formatted_buyer_brief_rows = []
    for id_num, buyer_with_briefs in buyers_dict.items():
        buyer_with_briefs['briefs'] = '; '.join(buyer_with_briefs['briefs'])
        formatted_buyer_brief_rows.append([buyer_with_briefs.get(header, '') for header in buyer_headings])

    formatted_buyer_brief_rows.sort(key=lambda x: x[0])
    formatted_buyer_brief_rows.insert(0, buyer_headings)

    timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%S')

    return Response(
        csv_generator.iter_csv(formatted_buyer_brief_rows),
        mimetype='text/csv',
        headers={
            "Content-Disposition": "attachment;filename=buyers_{}.csv".format(timestamp),
            "Content-Type": "text/csv; header=present"
        }
    )
