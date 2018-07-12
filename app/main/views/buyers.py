from dmapiclient import HTTPError
from dmutils.flask import timed_render_template as render_template
from flask import flash, redirect, request, url_for
from flask_login import current_user

from .. import main
from ..auth import role_required
from ..forms import EmailDomainForm
from ... import data_api_client


ADDED_BUYER_DOMAIN_MESSAGE = 'You’ve added {buyer_domain}.'
NO_BRIEFS_ERROR_MESSAGE = "There are no opportunities with ID {brief_id}"


@main.route('/buyers', methods=['GET'])
@role_required('admin', 'admin-ccs-category')
def find_buyer_by_brief_id():
    brief_id = request.args.get('brief_id')
    brief = None
    status_code = 200

    try:
        brief = data_api_client.get_brief(brief_id)
    except HTTPError:
        if 'brief_id' in request.args:
            flash(NO_BRIEFS_ERROR_MESSAGE.format(brief_id=brief_id), 'error')
            status_code = 404

    return render_template(
        "view_buyers.html",
        brief=brief.get('briefs') if brief else None,
        brief_id=brief_id
    ), status_code


@main.route('/buyers/add-buyer-domains', methods=['GET', 'POST'])
@role_required('admin')
def add_buyer_domains():
    email_domain_form = EmailDomainForm()
    status_code = 200
    if email_domain_form.validate_on_submit():
        try:
            new_domain = request.form.get('new_buyer_domain')
            data_api_client.create_buyer_email_domain(new_domain, current_user.email_address)
            flash(ADDED_BUYER_DOMAIN_MESSAGE.format(buyer_domain=new_domain))
            return redirect(url_for('.add_buyer_domains'))
        except HTTPError as e:
            status_code = 400
            if "has already been approved" in e.message:
                email_domain_form.new_buyer_domain.errors.append(
                    'You cannot add this domain because it already exists.'
                )
            elif "was not a valid format" in e.message:
                email_domain_form.new_buyer_domain.errors.append(
                    "‘{}’ is not a valid format.".format(new_domain)
                )
            else:
                raise e
    elif email_domain_form.new_buyer_domain.errors:
        status_code = 400

    return render_template(
        "add_buyer_email_domain.html",
        email_domain_form=email_domain_form
    ), status_code
