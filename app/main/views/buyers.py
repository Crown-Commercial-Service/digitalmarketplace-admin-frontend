from flask import render_template, request
from flask_login import login_required

from .. import main
from ... import data_api_client
from ..auth import role_required

@main.route('/buyers', methods=['GET'])
@login_required
@role_required('admin')
def find_buyer_by_brief_id():
    brief = data_api_client.get_brief(request.args.get('brief_id'))
    if brief:
        users = brief.get('briefs').get('users')
        return render_template(
            "view_buyers.html",
            users=users
        )
