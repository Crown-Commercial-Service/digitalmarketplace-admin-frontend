from __future__ import unicode_literals

from collections import OrderedDict
from datetime import datetime
from itertools import chain

from dmutils import csv_generator
from flask import render_template, request, Response
from flask_login import flash
from six import itervalues, iterkeys

from .. import main
from ..auth import role_required
from ... import data_api_client

CLOSED_BRIEF_STATUSES = ['closed', 'awarded', 'cancelled', 'unsuccessful']


@main.route('/users', methods=['GET'])
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
@role_required('admin-framework-manager')
def list_frameworks_with_users(errors=None):
    bad_statuses = ['coming', 'expired']
    frameworks = [framework for framework in data_api_client.find_frameworks()['frameworks']
                  if framework['status'] not in bad_statuses
                  #  TODO: remove this temporary hack once we have implemented new status that covers the DOS case
                  or framework['slug'] == 'digital-outcomes-and-specialists']
    framework_options = [{'value': framework['slug'], 'label': framework['name']} for framework
                         in sorted(frameworks, key=lambda framework: framework['name'])]

    return render_template(
        "download_users.html",
        framework_options=framework_options,
        errors=errors
    ), 200 if not errors else 400


@main.route('/users/download/<framework_slug>', methods=['GET'])
@role_required('admin')
def download_users(framework_slug):
    supplier_rows = data_api_client.export_users(framework_slug).get('users', [])
    supplier_headers = [
        "email address",
        "user_name",
        "supplier_id",
        "declaration_status",
        "application_status",
        "application_result",
        "framework_agreement",
        "variations_agreed"
    ]

    formatted_rows = []
    for row in supplier_rows:
        formatted_rows.append([row[heading] for heading in supplier_headers])
    formatted_rows.insert(0, supplier_headers)

    return Response(
        csv_generator.iter_csv(formatted_rows),
        mimetype='text/csv',
        headers={
            "Content-Disposition": "attachment;filename=users-{}.csv".format(framework_slug),
            "Content-Type": "text/csv; header=present"
        }
    )


@main.route('/users/download/buyers', methods=['GET'])
@role_required('admin')
def download_buyers_and_briefs():
    users = {user["id"]: dict(user, briefs=[]) for user in data_api_client.find_users_iter(role="buyer")}

    # join users with briefs (a "hash join")
    for brief in data_api_client.find_briefs_iter(with_users=True):
        for user in brief["users"]:
            users[user["id"]]["briefs"].append(brief)

    # not using DATETIME_FORMAT as we'll be using this in a filename and don't want any odd characters
    timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%S')

    # "verbatim" fields have the same column heading as the dict key they're retrieved from
    user_verbatim_fields = (
        "name",
        "emailAddress",
        "phoneNumber",
    )
    # "generated" fields have a column heading "label" and callable to generate the field value given a user(/brief)
    user_generated_fields = OrderedDict((
        (
            "createdAtDate",
            lambda brief: brief.get("createdAt", "").partition("T")[0],  # cheap truncation of iso timestamp
        ),
    ))
    brief_verbatim_fields = (
        "id",
        "title",
        "location",
        "lotSlug",
    )
    brief_generated_fields = OrderedDict((
        (
            "status",
            lambda brief: "open" if brief.get("status") == "live" else brief.get("status", ""),
        ),
        (
            "applicationsClosedAtDateIfClosed",
            lambda brief:
                (
                    brief.get("applicationsClosedAt", "") if brief.get("status") in CLOSED_BRIEF_STATUSES else ""
                ).partition("T")[0],
        ),
    ))

    rows_iter = chain(
        (
            # header row
            tuple(chain(
                ("user.{}".format(field_name) for field_name in user_verbatim_fields),
                ("user.{}".format(field_name) for field_name in iterkeys(user_generated_fields)),
                ("brief.{}".format(field_name) for field_name in brief_verbatim_fields),
                ("brief.{}".format(field_name) for field_name in iterkeys(brief_generated_fields)),
            )),
        ),
        (
            # data rows
            tuple(chain(
                (user.get(field_name, "") for field_name in user_verbatim_fields),
                (func(user) for func in itervalues(user_generated_fields)),
                (brief.get(field_name, "") for field_name in brief_verbatim_fields),
                (func(brief) for func in itervalues(brief_generated_fields)),
            ))
            for user, brief in chain.from_iterable(  # using from_iterable to flatten an iterable of iterables (of
                                                     # (user, brief) pairs) into a single iterable
                (
                    (user, brief) for brief in
                    (user["briefs"] or ({},))   # if user has an empty seq of briefs add a single fake blank
                                                # one ("outer join" behaviour)
                )
                for user in sorted(itervalues(users), key=lambda user: user["name"])
            )
        ),
    )

    return Response(
        csv_generator.iter_csv(rows_iter),
        mimetype='text/csv',
        headers={
            "Content-Disposition": "attachment;filename=buyers_{}.csv".format(timestamp),
            "Content-Type": "text/csv; header=present"
        }
    )
