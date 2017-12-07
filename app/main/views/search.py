from flask import render_template, request, redirect, url_for, flash
from flask_login import current_user

from ... import data_api_client
from .. import main

from dmapiclient import HTTPError
from ..auth import role_required


@main.route('/find-suppliers-and-services', methods=['GET'])
@role_required('admin', 'admin-ccs-category', 'admin-ccs-sourcing', 'admin-framework-manager')
def find_suppliers_and_services():
    return render_template("find_suppliers_and_services.html")
