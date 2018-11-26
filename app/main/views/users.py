from datetime import datetime

from dmutils import csv_generator, s3
from dmutils.documents import get_signed_url
from dmutils.flask import timed_render_template as render_template
from flask import abort, current_app, flash, redirect, request, Response, url_for
from flask_login import current_user

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
            flash("Sorry, we couldn't find an account with that email address", 'error')
            response_code = 404

    return render_template(
        "view_users.html",
        users=[users['users']] if users else list(),
        email_address=email_address
    ), response_code


@main.route('/frameworks/<framework_slug>/users', methods=['GET'])
@role_required('admin-framework-manager', 'admin-ccs-category', 'admin-ccs-data-controller')
def user_list_page_for_framework(framework_slug):
    bad_statuses = ['coming', 'expired']
    framework = data_api_client.get_framework(framework_slug).get("frameworks")
    # TODO replace this temporary fix for DOS2 when a better solution has been created.
    if not framework or \
            (framework['status'] in bad_statuses and framework['slug'] != 'digital-outcomes-and-specialists-2'):
        abort(404)

    supplier_csv_url = url_for(
        '.download_supplier_user_list_report', framework_slug=framework_slug, report_type='official'
    )
    user_csv_url = url_for(
        '.download_supplier_user_list_report', framework_slug=framework_slug, report_type='accounts'
    )

    return render_template(
        "download_framework_users.html",
        framework=framework,
        supplier_csv_url=supplier_csv_url,
        user_csv_url=user_csv_url,
    ), 200


@main.route('/frameworks/<framework_slug>/users/<report_type>/download', methods=['GET'])
@role_required('admin-framework-manager', 'admin-ccs-category', 'admin-ccs-data-controller')
def download_supplier_user_list_report(framework_slug, report_type):
    reports_bucket = s3.S3(current_app.config['DM_REPORTS_BUCKET'])

    if report_type == 'official':
        path = f"{framework_slug}/reports/official-details-for-suppliers-{framework_slug}.csv"
    elif report_type == 'accounts':
        path = f"{framework_slug}/reports/all-email-accounts-for-suppliers-{framework_slug}.csv"
    else:
        abort(404)

    url = get_signed_url(reports_bucket, path, current_app.config['DM_ASSETS_URL'])
    if not url:
        abort(404)

    return redirect(url)


@main.route('/users/download/suppliers', methods=['GET'])
@role_required('admin')
def supplier_user_research_participants_by_framework():
    bad_statuses = ['coming', 'expired']
    frameworks = data_api_client.find_frameworks().get("frameworks")
    frameworks = sorted(
        filter(
            lambda i: i['status'] not in bad_statuses or i['slug'] == 'digital-outcomes-and-specialists-2', frameworks
        ), key=lambda i: i['name']
    )

    items = [
        {
            "title": "User research participants on {}".format(framework['name']),
            "link": url_for('.download_supplier_user_research_report', framework_slug=framework['slug']),
            "file_type": "CSV"
        }
        for framework in frameworks
    ]
    return render_template(
        "user_research_participants.html",
        items=items
    ), 200


@main.route('/frameworks/<framework_slug>/user-research/download', methods=['GET'])
@role_required('admin')
def download_supplier_user_research_report(framework_slug):

    reports_bucket = s3.S3(current_app.config['DM_REPORTS_BUCKET'])
    path = "{framework_slug}/reports/user-research-suppliers-on-{framework_slug}.csv"
    url = get_signed_url(
        reports_bucket, path.format(framework_slug=framework_slug), current_app.config['DM_ASSETS_URL']
    )
    if not url:
        abort(404)

    return redirect(url)


@main.route('/users/download/buyers', methods=['GET'])
@role_required('admin-framework-manager', 'admin')
def download_buyers():
    """Either download a list of all buyers (for framework manager) or user research buyers (for admin users)."""
    download_filename = "all-buyers-on-{}.csv".format(datetime.utcnow().strftime('%Y-%m-%d-at-%H-%M-%S'))
    users = data_api_client.find_users_iter(role="buyer")

    if current_user.role == 'admin':
        # Overwrite the above values for admin specific user research csv
        download_filename = "user-research-buyers-on-{}.csv".format(datetime.utcnow().strftime('%Y-%m-%d-at-%H-%M-%S'))
        users = filter(lambda i: i['userResearchOptedIn'], users)

    header_row = ("email address", "name")
    user_attributes = ("emailAddress", "name")

    def rows_iter():
        """Iterator yielding header then rows."""
        yield header_row
        for user in sorted(users, key=lambda user: user["name"]):
            yield (user.get(field_name, "") for field_name in user_attributes)

    return Response(
        csv_generator.iter_csv(rows_iter()),
        mimetype='text/csv',
        headers={
            "Content-Disposition": "attachment;filename={}".format(download_filename),
            "Content-Type": "text/csv; header=present"
        }
    )
