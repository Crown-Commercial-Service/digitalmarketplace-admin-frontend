from datetime import datetime

from dmutils import s3
from dmutils.documents import get_signed_url
from dmutils.flask import timed_render_template as render_template
from flask import abort, current_app, flash, redirect, request, Response, url_for

from ..helpers.user_downloads import generate_user_csv
from .. import main
from ..auth import role_required
from ... import data_api_client

CLOSED_BRIEF_STATUSES = ['closed', 'awarded', 'cancelled', 'unsuccessful']


@main.route('/users', methods=['GET'])
@role_required('admin', 'admin-ccs-category', 'admin-ccs-data-controller')
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
    framework = data_api_client.get_framework(framework_slug).get("frameworks")
    if framework is None or framework['status'] == 'coming' or (
        framework['status'] == 'expired' and framework['family'] != 'digital-outcomes-and-specialists'
    ):
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
@role_required('admin-framework-manager')
def supplier_user_research_participants_by_framework():
    frameworks = data_api_client.find_frameworks().get("frameworks")
    frameworks = sorted(
        (fw for fw in frameworks if not (fw['status'] == 'coming' or (
            fw['status'] == 'expired' and fw['family'] != 'digital-outcomes-and-specialists'
        ))),
        key=lambda i: i['name'],
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
@role_required('admin-framework-manager')
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
@role_required('admin-framework-manager')
def download_buyers():
    """Download a list of all buyers"""
    download_filename = "all-buyers-on-{}.csv".format(datetime.utcnow().strftime('%Y-%m-%d-at-%H-%M-%S'))
    users = data_api_client.find_users_iter(role="buyer")

    return Response(
        generate_user_csv(users),
        mimetype='text/csv',
        headers={
            "Content-Disposition": "attachment;filename={}".format(download_filename),
            "Content-Type": "text/csv; header=present"
        }
    )


@main.route('/users/download/buyers/user-research', methods=['GET'])
@role_required('admin-framework-manager')
def download_buyers_for_user_research():
    """Download a list of buyers who have opted in to user research."""
    users = data_api_client.find_users_iter(role="buyer")
    # TODO: add param to API endpoint to filter by userResearchOptedIn
    users = filter(lambda i: i['userResearchOptedIn'], users)

    download_filename = "user-research-buyers-on-{}.csv".format(datetime.utcnow().strftime('%Y-%m-%d-at-%H-%M-%S'))

    return Response(
        generate_user_csv(users),
        mimetype='text/csv',
        headers={
            "Content-Disposition": "attachment;filename={}".format(download_filename),
            "Content-Type": "text/csv; header=present"
        }
    )
