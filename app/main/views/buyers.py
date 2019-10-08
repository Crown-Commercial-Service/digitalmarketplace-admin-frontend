from dmutils.forms import render_template_with_csrf
from flask import render_template, request, flash, jsonify, url_for, redirect
from flask_login import login_required, current_user
from react.render import render_component

from .. import main
from ... import data_api_client
from ..auth import role_required
from dmapiclient.errors import HTTPError


NEW_LINE = '\n'
AREA_OF_EXPERTISE_LIST = [
    'Agile delivery and Governance',
    'Content and Publishing',
    'Cyber security',
    'Data science',
    'Emerging technologies',
    'Marketing, Communications and Engagement',
    'Software engineering and Development',
    'Strategy and Policy',
    'Support and Operations',
    'User research and Design',
    'Change and Transformation',
    'Training, Learning and Development'
]


@main.route('/buyers/<int:brief_id>/edit', methods=['GET'])
@login_required
@role_required('admin')
def brief_edit_json(brief_id):
    brief = data_api_client.get_brief(brief_id).get('briefs')

    rendered_component = render_component(
        'bundles/ApplicationsAdmin/BriefAdminWidget.js',
        {
            'brief': brief,
            'meta': {
                'url_brief_update': url_for('.update_brief_data', brief_id=brief_id),
            }
        }
    )

    return render_template(
        '_react.html',
        component=rendered_component
    )


@main.route('/buyers/<int:brief_id>/update', methods=['POST'])
@login_required
@role_required('admin')
def update_brief_data(brief_id):
    json_payload = request.get_json(force=True)
    result = (data_api_client
              .req
              .briefs(brief_id)
              .json()
              .admin()
              .put({"brief": json_payload}))

    return jsonify(result)


@main.route('/buyers', methods=['GET'])
@login_required
@role_required('admin')
def find_buyer_by_brief_id():
    brief_id = request.args.get('brief_id')
    teams = []

    try:
        brief = data_api_client.get_brief(brief_id).get('briefs')
        teams = data_api_client.req.admin().buyers(brief_id).teams().get()

    except:  # noqa
        flash('no_brief', 'error')
        return render_template(
            "view_buyers.html",
            users=list(),
            brief_id=brief_id,
            brief=None
        ), 404

    users = brief.get('users')
    title = brief.get('title')

    return render_template_with_csrf(
        "view_buyers.html",
        users=users,
        title=title,
        brief_id=brief_id,
        brief=brief,
        seller_email_list=convert_array_to_string(brief.get('sellerEmailList', [])),
        seller_email=brief.get('sellerEmail', ''),
        area_of_expertise_list=AREA_OF_EXPERTISE_LIST,
        area_of_expertise_selected=brief.get('areaOfExpertise', ''),
        teams_exists=len(teams) > 0,
        teams=teams
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
        elif request.form.get('questions_closed_at'):
            brief = data_api_client.req.briefs(brief_id).admin() \
                .post({'briefs': {'clarification_questions_closed_at': request.form['questions_closed_at'],
                                  'applications_closed_at': request.form['closed_at']
                                  },
                       'update_details': {'updated_by': current_user.email_address}}).get('briefs')
        elif request.form.get('add_seller_to_rfx_brief'):
            brief = (
                data_api_client
                .req
                .briefs(brief_id)
                .suppliers(
                    request.form['add_seller_to_rfx_brief'].strip()
                )
                .put({
                    'update_details': {
                        'updated_by': current_user.email_address
                    }
                })
                .get('briefs')
            )
        elif request.form.get('remove_seller_from_rfx_brief'):
            brief = (
                data_api_client
                .req
                .briefs(brief_id)
                .suppliers(
                    request.form['remove_seller_from_rfx_brief'].strip()
                )
                .delete({
                    'update_details': {
                        'updated_by': current_user.email_address
                    }
                })
                .get('briefs'))
        elif 'edit_seller_email_list' in request.form:
            edit_seller_email_list = request.form.get('edit_seller_email_list', []).split(NEW_LINE)
            brief = data_api_client.req.briefs(brief_id).admin() \
                .post({
                    'briefs': {
                        'sellerEmailList': [_.strip() for _ in edit_seller_email_list if _ != '']
                    },
                    'update_details': {'updated_by': current_user.email_address}
                }).get('briefs')
        elif 'edit_seller_email' in request.form:
            edit_seller_email = request.form.get('edit_seller_email', '')
            brief = data_api_client.req.briefs(brief_id).admin() \
                .post({
                    'briefs': {
                        'sellerEmail': edit_seller_email
                    },
                    'update_details': {'updated_by': current_user.email_address}
                }).get('briefs')
        elif 'edit_area_of_expertise' in request.form:
            brief = data_api_client.req.briefs(brief_id).admin() \
                .post({'briefs': {'areaOfExpertise': request.form['edit_area_of_expertise']
                                  },
                       'update_details': {'updated_by': current_user.email_address}}).get('briefs')
        else:
            brief = data_api_client.get_brief(brief_id).get('briefs')

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
        brief=brief,
        seller_email_list=convert_array_to_string(brief.get('sellerEmailList', [])),
        seller_email=brief.get('sellerEmail', ''),
        area_of_expertise_list=AREA_OF_EXPERTISE_LIST,
        area_of_expertise_selected=brief.get('areaOfExpertise', '')
    )


@main.route('/brief/<int:brief_id>/withdraw', methods=['POST'])
@login_required
@role_required('admin')
def withdraw_brief(brief_id):
    try:
        brief = data_api_client.req.briefs(brief_id).withdraw().post({
            'update_details': {'updated_by': current_user.email_address}
        }).get('briefs')
    except HTTPError, e:
        flash(e.message, 'error')
        brief = data_api_client.get_brief(brief_id).get('briefs')

        return render_template_with_csrf(
            'view_buyers.html',
            users=brief.get('users'),
            title=brief.get('title'),
            brief_id=brief_id,
            brief=brief
        )

    flash('brief_withdrawn', 'info')
    return render_template_with_csrf(
        'view_buyers.html',
        users=brief.get('users'),
        title=brief.get('title'),
        brief_id=brief_id,
        brief=brief,
        seller_email_list=convert_array_to_string(brief.get('sellerEmailList', [])),
        seller_email=brief.get('sellerEmail', ''),
        area_of_expertise_list=AREA_OF_EXPERTISE_LIST,
        area_of_expertise_selected=brief.get('areaOfExpertise', '')
    )


def convert_array_to_string(array):
    return NEW_LINE.join(array)


@main.route('/brief/<int:brief_id>/seller-feedback-email', methods=['POST'])
@login_required
@role_required('admin')
def seller_feedback_email(brief_id):
    (
        data_api_client
        .req
        .briefs(brief_id)
        .send_feedback_email()
        .post({
            'update_details': {'updated_by': current_user.email_address}
        })
    )

    flash('seller_feedback_email', 'info')
    return redirect(url_for('.find_buyer_by_brief_id', brief_id=brief_id))


@main.route('/team', methods=['GET'])
@login_required
@role_required('admin')
def find_team_by_team_id():
    team_id = request.args.get('team_id')

    team_info = data_api_client.req.admin().team(team_id).get()
    team = team_info.get('team')
    briefs = team_info.get('briefs')

    return render_template_with_csrf(
        "view_teams.html",
        team_id=team_id,
        team=team,
        briefs=briefs
    )


@main.route('/', methods=['GET'])
@login_required
@role_required('admin')
def find_brief_by_team_id():
    team_id = request.args.get('team_id')

    team_info = data_api_client.req.admin().team(team_id).get()
    team = team_info.get('team')
    briefs = team_info.get('briefs')

    return render_template_with_csrf(
        "view_teams.html",
        team_id=team_id,
        team=team
    )
