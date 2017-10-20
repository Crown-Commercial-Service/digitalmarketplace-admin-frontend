from dmapiclient import HTTPError
from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user

from ..forms import EmailDomainForm
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


@main.route('/buyers/add-buyer-domains', methods=['GET', 'POST'])
@role_required('admin')
def add_buyer_domains():
    email_domain_form = EmailDomainForm()

    if email_domain_form.validate_on_submit():
        try:
            new_domain = request.form.get('new_buyer_domain')
            data_api_client.create_buyer_email_domain(new_domain, current_user.email_address)
            flash('You’ve added {}.'.format(new_domain), 'message')
            return redirect(url_for('.add_buyer_domains'))
        except HTTPError as e:
            if "has already been approved" in e.message:
                flash('You cannot add this domain because it already exists.', 'error')
            elif "was not a valid format" in e.message:
                flash('The domain {} is not a valid format'.format(new_domain), 'error')

    return render_template(
        "add_buyer_email_domain.html",
        email_domain_form=email_domain_form
    ), 400 if email_domain_form.new_buyer_domain.errors else 200
