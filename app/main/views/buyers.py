from flask import render_template, request, flash
from flask_login import login_required

from .. import main
from ... import data_api_client
from ..auth import role_required


@main.route('/buyers', methods=['GET'])
@login_required
@role_required('admin')
def find_buyer_by_opportunity_id():
    opportunity_id = request.args.get('opportunity_id')

    try:
        opportunity = data_api_client.get_brief(opportunity_id).get('briefs')

    except:
        flash('no_opportunity', 'error')
        return render_template(
            "view_buyers.html",
            users=list(),
            opportunity_id=opportunity_id
        ), 404

    users = opportunity.get('users')
    title = opportunity.get('title')
    return render_template(
        "view_buyers.html",
        users=users,
        title=title,
        opportunity_id=opportunity_id
    )
