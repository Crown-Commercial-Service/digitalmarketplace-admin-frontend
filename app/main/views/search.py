from flask import render_template
from .. import main
from ..auth import role_required


@main.route('/find-suppliers-and-services', methods=['GET'])
@role_required('admin', 'admin-ccs-category', 'admin-ccs-sourcing', 'admin-framework-manager')
def find_suppliers_and_services():
    return render_template("find_suppliers_and_services.html")
