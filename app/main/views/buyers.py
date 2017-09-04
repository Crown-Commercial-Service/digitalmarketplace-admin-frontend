from flask import render_template, request, flash

from .. import main
from ... import data_api_client
from ..auth import role_required


@main.route('/buyers', methods=['GET'])
@role_required('admin')
def find_buyer_by_brief_id():
    brief_id = request.args.get('brief_id')

    try:
        brief = data_api_client.get_brief(brief_id).get('briefs')

    except:
        flash('no_brief', 'error')
        return render_template(
            "view_buyers.html",
            users=list(),
            brief_id=brief_id
        ), 404

    users = brief.get('users')
    title = brief.get('title')
    return render_template(
        "view_buyers.html",
        users=users,
        title=title,
        brief_id=brief_id
    )
