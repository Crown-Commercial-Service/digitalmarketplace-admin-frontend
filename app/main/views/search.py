from dmutils.flask import timed_render_template as render_template

from .. import main
from ..auth import role_required


@main.route('/search', methods=['GET'])
@role_required('admin-ccs-data-controller', 'admin', 'admin-ccs-category', 'admin-ccs-sourcing',
               'admin-framework-manager')
def search_suppliers_and_services():
    return render_template("search/search.html")
