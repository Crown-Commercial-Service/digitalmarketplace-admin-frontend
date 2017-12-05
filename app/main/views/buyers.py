from dmutils.forms import render_template_with_csrf
from flask import render_template, request, flash, jsonify
from flask_login import login_required, current_user

from .. import main
from ... import data_api_client
from ..auth import role_required
from dmapiclient.errors import HTTPError


@main.route('/buyers', methods=['GET'])
@login_required
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
    return render_template_with_csrf(
        "view_buyers.html",
        users=users,
        title=title,
        brief_id=brief_id,
        brief=brief
    )


@main.route('/brief/<int:brief_id>', methods=['POST'])
@login_required
@role_required('admin')
def update_brief(brief_id):
    try:
        if request.form.get('add_user'):
            brief = data_api_client.req.briefs(brief_id).users(request.form['add_user'].strip()) \
                .put({'update_details': {'updated_by': current_user.email_address}}).get('briefs')
        elif request.form.get('remove_user'):
            brief = data_api_client.req.briefs(brief_id).users(request.form['remove_user'].strip()) \
                .delete({'update_details': {'updated_by': current_user.email_address}}).get('briefs')
        else:
            brief = data_api_client.req.briefs(brief_id).admin() \
                .post({'briefs': {'clarification_questions_closed_at': request.form['questions_closed_at'],
                                  'applications_closed_at': request.form['closed_at']
                                  },
                       'update_details': {'updated_by': current_user.email_address}}).get('briefs')
    except HTTPError, e:
        flash(e.message, 'error')
        brief = data_api_client.get_brief(brief_id).get('briefs')
        users = brief.get('users')
        title = brief.get('title')
        return render_template_with_csrf(
            "view_buyers.html",
            users=users,
            title=title,
            brief_id=brief_id,
            brief=brief
        )

    flash('brief_updated', 'info')
    users = brief.get('users')
    title = brief.get('title')
    return render_template_with_csrf(
        "view_buyers.html",
        users=users,
        title=title,
        brief_id=brief_id,
        brief=brief
    )
