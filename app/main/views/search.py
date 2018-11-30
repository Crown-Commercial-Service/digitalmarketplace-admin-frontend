from dmutils.flask import timed_render_template as render_template

from .. import main
from ..auth import role_required


# TODO: merge old search page with new combined search box below
@main.route('/find-suppliers-and-services', methods=['GET'])
@role_required('admin', 'admin-ccs-category', 'admin-ccs-sourcing', 'admin-framework-manager')
def find_suppliers_and_services():
    return render_template("find_suppliers_and_services.html")


@main.route('/search', methods=['GET'])
@role_required('admin-ccs-data-controller')
def search_suppliers_and_services():
    return render_template("search/search.html")
