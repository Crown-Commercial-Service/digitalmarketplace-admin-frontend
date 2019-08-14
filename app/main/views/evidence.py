from flask import request, jsonify, abort, redirect
from flask_login import login_required, current_user

from .. import main
from ... import data_api_client
from ..auth import role_required

from react.render import render_component


@main.route('/evidence/delete/<int:evidence_id>', methods=['POST'])
@login_required
@role_required('admin')
def evidence_delete_draft(evidence_id):
    supplier_code = request.args.get('supplier_code', None)
    if not supplier_code:
        abort(400, 'must supply the supplier code')
    result = data_api_client.req.evidence(evidence_id).delete({'actioned_by': current_user.id})
    return redirect('/admin/suppliers/services?supplier_code={}'.format(supplier_code))
