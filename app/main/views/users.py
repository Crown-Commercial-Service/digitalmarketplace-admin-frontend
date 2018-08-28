from datetime import datetime

from dmutils import csv_generator
from dmutils.config import convert_to_boolean
from dmutils.flask import timed_render_template as render_template
from flask import abort, flash, request, Response, url_for
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
@role_required('admin-framework-manager', 'admin-ccs-category')
def user_list_page_for_framework(framework_slug):
    bad_statuses = ['coming', 'expired']
    framework = data_api_client.get_framework(framework_slug).get("frameworks")
    if not framework or framework['status'] in bad_statuses:
        abort(404)

    return render_template(
        "download_framework_users.html",
        framework=framework,
    ), 200


@main.route('/users/download/suppliers', methods=['GET'])
@role_required('admin')
def supplier_user_research_participants_by_framework():
    bad_statuses = ['coming', 'expired']
    frameworks = data_api_client.find_frameworks().get("frameworks")
    frameworks = sorted(filter(lambda i: i['status'] not in bad_statuses, frameworks), key=lambda i: i['name'])
    items = [
        {
            "title": "User research participants on {}".format(framework['name']),
            "link": url_for('.download_users', framework_slug=framework['slug'], user_research_opted_in=True),
            "file_type": "CSV"
        }
        for framework in frameworks
    ]
    return render_template(
        "user_research_participants.html",
        items=items
    ), 200


@main.route('/frameworks/<framework_slug>/users/download', methods=['GET'])
@role_required('admin-framework-manager', 'admin', 'admin-ccs-category')
def download_users(framework_slug):
    user_research_opted_in = convert_to_boolean(request.args.get('user_research_opted_in'))

    if (
        current_user.role == 'admin' and not user_research_opted_in or
        current_user.role == 'admin-framework-manager' and user_research_opted_in or
        current_user.role == 'admin-ccs-category' and user_research_opted_in
    ):
        abort(403)

    supplier_rows = data_api_client.export_users(framework_slug).get('users', [])
    supplier_headers = [
        "email address",
        "user_name",
        "supplier_id",
        "declaration_status",
        "application_status",
        "application_result",
        "framework_agreement",
        "variations_agreed",
        "published_service_count"
    ]
    if user_research_opted_in:
        supplier_rows = [row for row in supplier_rows if row['user_research_opted_in']]
        download_filename = "user-research-suppliers-on-{}.csv".format(framework_slug)
    else:

        download_filename = "all-email-accounts-for-suppliers-{}.csv".format(framework_slug)
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


@main.route('/frameworks/<framework_slug>/suppliers/download', methods=['GET'])
@role_required('admin-framework-manager', 'admin-ccs-category')
def download_suppliers(framework_slug):
    framework = data_api_client.get_framework(framework_slug).get("frameworks")

    supplier_rows = data_api_client.export_suppliers(framework_slug).get('suppliers', [])

    supplier_and_framework_headers = [
        "supplier_id",
        "supplier_name",
        "supplier_organisation_size",
        "duns_number",
        "companies_house_number",
        "registered_name",
        "declaration_status",
        "application_status",
        "application_result",
        "framework_agreement",
        "variations_agreed",
    ]
    service_count_headers = [lot['slug'] for lot in framework['lots']]
    contact_info_headers = [
        'contact_name',
        'contact_email',
        'contact_phone_number',
        'address_first_line',
        'address_city',
        'address_postcode',
        'address_country',
    ]

    download_filename = "official-details-for-suppliers-{}.csv".format(framework_slug)

    formatted_rows = [
        supplier_and_framework_headers +
        ["total_number_of_services"] +
        ["service-count-{}".format(h) for h in service_count_headers] +
        contact_info_headers
    ]
    for row in supplier_rows:
        # Include an extra column with the total number of services across all lots
        service_counts = [row['published_services_count'][heading] for heading in service_count_headers]
        total_number_of_services = sum(service_counts)

        formatted_rows.append(
            [row[heading] for heading in supplier_and_framework_headers] +
            [total_number_of_services] +
            service_counts +
            [row['contact_information'][heading] for heading in contact_info_headers]
        )

    return Response(
        csv_generator.iter_csv(formatted_rows),
        mimetype='text/csv',
        headers={
            "Content-Disposition": "attachment;filename={}".format(download_filename),
            "Content-Type": "text/csv; header=present"
        }
    )


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
