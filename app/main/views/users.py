from __future__ import unicode_literals

from datetime import datetime
from itertools import chain

from dmutils import csv_generator
from flask import abort, render_template, request, Response
from flask_login import flash

from .. import main
from ..auth import role_required
from ... import data_api_client

CLOSED_BRIEF_STATUSES = ['closed', 'awarded', 'cancelled', 'unsuccessful']


@main.route('/users', methods=['GET'])
@role_required('admin', 'admin-ccs-category')
def find_user_by_email_address():
    users = None
    email_address = None
    response_code = 200

    if "email_address" in request.args:
        email_address = request.args.get("email_address")
        if email_address:
            users = data_api_client.get_user(email_address=email_address)
        if not users:
            flash('no_users', 'error')
            response_code = 404

    return render_template(
        "view_users.html",
        users=[users['users']] if users else list(),
        email_address=email_address
    ), response_code


@main.route('/frameworks/<framework_slug>/users', methods=['GET'])
@role_required('admin-framework-manager')
def user_list_page_for_framework(framework_slug):
    bad_statuses = ['coming', 'expired']
    framework = data_api_client.get_framework(framework_slug).get("frameworks")
    if not framework or framework['status'] in bad_statuses:
        abort(404)

    return render_template(
        "download_framework_users.html",
        framework=framework,
    ), 200


@main.route('/frameworks/<framework_slug>/users/download', methods=['GET'])
@role_required('admin-framework-manager')
def download_users(framework_slug):
    on_framework_only = request.args.get('on_framework_only')
    supplier_rows = data_api_client.export_users(framework_slug).get('users', [])
    on_framework_only_headers = [
        "email address",
        "user_name",
        "supplier_id",
    ]
    additional_full_headers = [
        "declaration_status",
        "application_status",
        "application_result",
        "framework_agreement",
        "variations_agreed"
    ]

    if on_framework_only:
        supplier_headers = on_framework_only_headers
        supplier_rows = [row for row in supplier_rows if row['application_result'] == 'pass']
        download_filename = "suppliers-on-{}.csv".format(framework_slug)
    else:
        supplier_headers = on_framework_only_headers + additional_full_headers
        download_filename = "{}-suppliers-who-applied-or-started-application.csv".format(framework_slug)
    formatted_rows = []
    for row in supplier_rows:
        formatted_rows.append([row[heading] for heading in supplier_headers])
    formatted_rows.insert(0, supplier_headers)

    return Response(
        csv_generator.iter_csv(formatted_rows),
        mimetype='text/csv',
        headers={
            "Content-Disposition": "attachment;filename={}".format(download_filename),
            "Content-Type": "text/csv; header=present"
        }
    )


@main.route('/users/download/buyers', methods=['GET'])
@role_required('admin-framework-manager')
def download_buyers():

    user_attributes = (
        "emailAddress",
        "name",
    )
    users = data_api_client.find_users_iter(role="buyer")

    rows_iter = chain(
        (
            # header row
            ("email address", "name"),
        ),
        (
            # data rows
            tuple(chain(
                (user.get(field_name, "") for field_name in user_attributes),
            ))
            for user in sorted(users, key=lambda user: user["name"])
        ),
    )

    return Response(
        csv_generator.iter_csv(rows_iter),
        mimetype='text/csv',
        headers={
            "Content-Disposition": "attachment;filename=all-buyers-on-{}.csv".format(
                datetime.utcnow().strftime('%Y-%m-%d-at-%H-%M-%S')
            ),
            "Content-Type": "text/csv; header=present"
        }
    )
