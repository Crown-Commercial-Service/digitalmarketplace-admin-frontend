from flask import render_template

from ... import data_api_client
from .. import main

from ..auth import role_required


@main.route('/admin-users', methods=['GET'])
@role_required('admin-manager')
def manage_admin_users():
    # The API doesn't support filtering users by multiple roles at once, and it's not worth adding that feature
    # just for this one view that (currently, and for the foreseeable future) will be very rarely used.
    # In future, if we have many many admin users and/or this page is heavily used we should:
    # (1) Fix the API to allow fetching all relevant user roles with a single call
    # (2) Stop using the _iter method and properly paginate this page

    support_users = data_api_client.find_users_iter(role='admin')
    category_users = data_api_client.find_users_iter(role='admin-ccs-category')
    sourcing_users = data_api_client.find_users_iter(role='admin-ccs-sourcing')

    # We want to sort so all Active users are above all Suspended users, and alphabetical by name within these groups.
    # In Python False < True (False is zero, True is one) so sorting on "active is False" puts Active users first.
    admin_users = sorted(
        list(support_users) + list(category_users) + list(sourcing_users),
        key=lambda k: (k['active'] is False, k['name'])
    )

    return render_template("view_admin_users.html",
                           admin_users=admin_users)
