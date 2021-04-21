from flask import render_template, request, redirect, url_for, abort, current_app
from flask_login import login_required, current_user
from flask import flash
from dateutil.parser import parse as parse_date
from react.render import render_component

from .. import main
from ... import data_api_client, content_loader
from app.main.forms import MoveUserForm, InviteForm, NewSellerUserForm
from ..auth import role_required

from dmapiclient import HTTPError, APIError
from dmapiclient.audit import AuditTypes
from dmutils.email import send_email, generate_token, EmailError
from dmutils.documents import (
    get_signed_url, get_agreement_document_path, file_is_pdf,
    AGREEMENT_FILENAME, SIGNED_AGREEMENT_PREFIX, COUNTERSIGNED_AGREEMENT_FILENAME,
)
from dmutils import s3
from dmutils.formats import DateFormatter
from dmutils.forms import DmForm, render_template_with_csrf
from ..forms import NewSellerUserForm
from itertools import chain

from urllib import quote_plus

import pendulum


@main.route('/suppliers', methods=['GET'])
@login_required
@role_required('admin', 'admin-ccs-category', 'admin-ccs-sourcing')
def find_suppliers():
    if request.args.get('supplier_code'):
        suppliers = [data_api_client.get_supplier(request.args.get('supplier_code'))['supplier']]
    else:
        suppliers = data_api_client.find_suppliers(
            prefix=request.args.get('supplier_name_prefix'),
            per_page=1000)['suppliers']  # hard coded to 1000 records, in hope this is enough for admins searching

    return render_template_with_csrf(
        "view_suppliers.html",
        suppliers=suppliers,
        signed_agreement_prefix=SIGNED_AGREEMENT_PREFIX,
        agreement_prefix=AGREEMENT_FILENAME
    )


@main.route('/suppliers/<string:supplier_code>/edit/name', methods=['GET'])
@login_required
@role_required('admin')
def edit_supplier_name(supplier_code):
    supplier = data_api_client.get_supplier(supplier_code)

    return render_template_with_csrf(
        "edit_supplier_name.html",
        supplier=supplier['supplier']
    )


@main.route('/suppliers/<string:supplier_code>/edit/declarations/<string:framework_slug>', methods=['GET'])
@login_required
@role_required('admin-ccs-sourcing')
def view_supplier_declaration(supplier_code, framework_slug):
    supplier = data_api_client.get_supplier(supplier_code)['supplier']
    framework = data_api_client.get_framework(framework_slug)['frameworks']
    if framework['status'] not in ['pending', 'standstill', 'live']:
        abort(403)
    try:
        declaration = data_api_client.get_supplier_declaration(supplier_code, framework_slug)['declaration']
    except APIError as e:
        if e.status_code != 404:
            raise
        declaration = {}

    content = content_loader.get_manifest(framework_slug, 'declaration').filter(declaration)

    return render_template_with_csrf(
        "suppliers/view_declaration.html",
        supplier=supplier,
        framework=framework,
        declaration=declaration,
        content=content
    )


@main.route('/suppliers/<supplier_code>/agreements/<framework_slug>/<document_name>', methods=['GET'])
@login_required
@role_required('admin', 'admin-ccs-sourcing')
def download_agreement_file(supplier_code, framework_slug, document_name):
    supplier_framework = data_api_client.get_supplier_framework_info(supplier_code, framework_slug)['frameworkInterest']
    if not supplier_framework.get('declaration'):
        abort(404)
    agreements_bucket = s3.S3(current_app.config['DM_AGREEMENTS_BUCKET'])
    prefix = get_agreement_document_path(framework_slug, supplier_code, document_name)
    agreement_documents = agreements_bucket.list(prefix=prefix)
    if not len(agreement_documents):
        abort(404)
    path = agreement_documents[-1]['path']
    url = get_signed_url(agreements_bucket, path, current_app.config['DM_ASSETS_URL'])
    if not url:
        abort(404)

    return redirect(url)


@main.route('/suppliers/<supplier_code>/countersigned-agreements/<framework_slug>',
            methods=['GET'])
@login_required
@role_required('admin-ccs-sourcing')
def list_countersigned_agreement_file(supplier_code, framework_slug):
    supplier = data_api_client.get_supplier(supplier_code)['supplier']
    framework = data_api_client.get_framework(framework_slug)['frameworks']
    agreements_bucket = s3.S3(current_app.config['DM_AGREEMENTS_BUCKET'])
    path = get_agreement_document_path(framework_slug, supplier_code, COUNTERSIGNED_AGREEMENT_FILENAME)
    countersigned_agreement_document = agreements_bucket.get_key(path)
    if countersigned_agreement_document:
        countersigned_agreement = countersigned_agreement_document
        date_formatter = DateFormatter(current_app.config['DM_TIMEZONE'])
        countersigned_agreement['last_modified'] = date_formatter.datetimeformat(parse_date(
            countersigned_agreement['last_modified']))
        countersigned_agreement = [countersigned_agreement]
    else:
        countersigned_agreement = []

    return render_template_with_csrf(
        "suppliers/upload_countersigned_agreement.html",
        supplier=supplier,
        framework=framework,
        countersigned_agreement=countersigned_agreement,
        countersigned_agreement_filename=COUNTERSIGNED_AGREEMENT_FILENAME
    )


@main.route('/suppliers/<supplier_code>/countersigned-agreements/<framework_slug>', methods=['POST'])
@login_required
@role_required('admin-ccs-sourcing')
def upload_countersigned_agreement_file(supplier_code, framework_slug):
    agreements_bucket = s3.S3(current_app.config['DM_AGREEMENTS_BUCKET'])
    errors = {}

    if request.files.get('countersigned_agreement'):
        the_file = request.files['countersigned_agreement']
        if not file_is_pdf(the_file):
            errors['countersigned_agreement'] = 'not_pdf'

        if 'countersigned_agreement' not in errors.keys():
            filename = get_agreement_document_path(framework_slug, supplier_code, COUNTERSIGNED_AGREEMENT_FILENAME)
            agreements_bucket.save(filename, the_file)

            data_api_client.create_audit_event(
                audit_type=AuditTypes.upload_countersigned_agreement,
                user=current_user.email_address,
                object_type='suppliers',
                object_id=supplier_code,
                data={'upload_countersigned_agreement': filename})

            flash('countersigned_agreement', 'upload_countersigned_agreement')

    if len(errors) > 0:
        for category, message in errors.items():
            flash(category, message)

    return redirect(url_for(
        '.list_countersigned_agreement_file',
        supplier_code=supplier_code,
        framework_slug=framework_slug)
    )


@main.route('/suppliers/<supplier_code>/countersigned-agreements-remove/<framework_slug>',
            methods=['GET', 'POST'])
@login_required
@role_required('admin-ccs-sourcing')
def remove_countersigned_agreement_file(supplier_code, framework_slug):
    agreements_bucket = s3.S3(current_app.config['DM_AGREEMENTS_BUCKET'])
    document = get_agreement_document_path(framework_slug, supplier_code, COUNTERSIGNED_AGREEMENT_FILENAME)

    if request.method == 'GET':
        flash('countersigned_agreement', 'remove_countersigned_agreement')

    if request.method == 'POST':
        agreements_bucket.delete_key(document)

        data_api_client.create_audit_event(
            audit_type=AuditTypes.delete_countersigned_agreement,
            user=current_user.email_address,
            object_type='suppliers',
            object_id=supplier_code,
            data={'upload_countersigned_agreement': document})

    return redirect(url_for(
        '.list_countersigned_agreement_file',
        supplier_code=supplier_code,
        framework_slug=framework_slug)
    )


@main.route(
    '/suppliers/<string:supplier_code>/edit/declarations/<string:framework_slug>/<string:section_id>',
    methods=['GET'])
@login_required
@role_required('admin-ccs-sourcing')
def edit_supplier_declaration_section(supplier_code, framework_slug, section_id):
    supplier = data_api_client.get_supplier(supplier_code)['supplier']
    framework = data_api_client.get_framework(framework_slug)['frameworks']
    if framework['status'] not in ['pending', 'standstill', 'live']:
        abort(403)
    try:
        declaration = data_api_client.get_supplier_declaration(supplier_code, framework_slug)['declaration']
    except APIError as e:
        if e.status_code != 404:
            raise
        declaration = {}

    content = content_loader.get_manifest(framework_slug, 'declaration').filter(declaration)
    section = content.get_section(section_id)
    if section is None:
        abort(404)

    return render_template_with_csrf(
        "suppliers/edit_declaration.html",
        supplier=supplier,
        framework=framework,
        declaration=declaration,
        section=section
    )


@main.route(
    '/suppliers/<string:supplier_code>/edit/declarations/<string:framework_slug>/<string:section_id>',
    methods=['POST'])
def update_supplier_declaration_section(supplier_code, framework_slug, section_id):
    supplier = data_api_client.get_supplier(supplier_code)['supplier']
    framework = data_api_client.get_framework(framework_slug)['frameworks']
    if framework['status'] not in ['pending', 'standstill', 'live']:
        abort(403)
    try:
        declaration = data_api_client.get_supplier_declaration(supplier_code, framework_slug)['declaration']
    except APIError as e:
        if e.status_code != 404:
            raise
        declaration = {}

    content = content_loader.get_manifest(framework_slug, 'declaration').filter(declaration)
    section = content.get_section(section_id)
    if section is None:
        abort(404)

    posted_data = section.get_data(request.form)

    if section.has_changes_to_save(declaration, posted_data):
        declaration.update(posted_data)
        data_api_client.set_supplier_declaration(
            supplier_code, framework_slug, declaration,
            current_user.email_address)

    return redirect(url_for('.view_supplier_declaration',
                            supplier_code=supplier_code, framework_slug=framework_slug))


@main.route('/suppliers/<string:supplier_code>/edit/name', methods=['POST'])
@login_required
@role_required('admin')
def update_supplier_name(supplier_code):
    supplier = data_api_client.get_supplier(supplier_code)
    new_supplier_name = request.form.get('new_supplier_name', '')

    data_api_client.update_supplier(supplier_code, {'name': new_supplier_name})

    return redirect(url_for('.find_suppliers', supplier_name_prefix=new_supplier_name[:1]))


@main.route('/suppliers/users', methods=['GET'])
@login_required
@role_required('admin', 'admin-ccs-category')
def find_supplier_users():

    if not request.args.get('supplier_code'):
        abort(404)

    supplier = data_api_client.get_supplier(request.args['supplier_code'])
    users = data_api_client.find_users(request.args.get('supplier_code'))

    return render_template_with_csrf(
        "view_supplier_users.html",
        users=users["users"],
        invite_form=InviteForm(),
        move_user_form=MoveUserForm(),
        new_seller_user_form=NewSellerUserForm(),
        supplier=supplier['supplier']
    )


@main.route('/suppliers/users/<int:user_id>/unlock', methods=['POST'])
@login_required
@role_required('admin')
def unlock_user(user_id):
    user = data_api_client.update_user(user_id, locked=False, updater=current_user.email_address)
    if "source" in request.form:
        return redirect(request.form["source"])
    return redirect(url_for('.find_supplier_users', supplier_code=user['users']['supplier']['supplierCode']))


@main.route('/suppliers/users/<int:user_id>/activate', methods=['POST'])
@login_required
@role_required('admin')
def activate_user(user_id):
    user = data_api_client.update_user(user_id, active=True, updater=current_user.email_address)
    if "source" in request.form:
        return redirect(request.form["source"])
    return redirect(url_for('.find_supplier_users', supplier_code=user['users']['supplier']['supplierCode']))


@main.route('/suppliers/users/<int:user_id>/deactivate', methods=['POST'])
@login_required
@role_required('admin')
def deactivate_user(user_id):
    user = data_api_client.update_user(user_id, active=False, updater=current_user.email_address)
    if "source" in request.form:
        return redirect(request.form["source"])
    return redirect(url_for('.find_supplier_users', supplier_code=user['users']['supplier']['supplierCode']))


@main.route('/suppliers/users/<int:user_id>/supplier_code/<int:supplier_code>/set-auth-rep', methods=['POST'])
@login_required
@role_required('admin')
def set_auth_rep_user(user_id, supplier_code):
    result = (
        data_api_client
        .req
        .suppliers(supplier_code)
        .users(user_id)
        .set_authorize_rep_user()
        .get()
    )

    if result['result'] == 'SUCCESS':
        return redirect(url_for('.find_supplier_users', supplier_code=supplier_code))
    else:
        return render_template_with_csrf('set_authorize_rep_user.html', supplier_code=supplier_code, user_id=user_id)


@main.route('/suppliers/users/<int:user_id>/reset_password', methods=['POST'])
@login_required
@role_required('admin')
def reset_password(user_id):
    user = data_api_client.get_user(user_id)
    result = data_api_client.req.users().resetpassword().post({
        'email_address': user['users']['emailAddress']
    })

    token = result['token']

    return redirect('{}://{}/2/reset-password/{}?e={}'.format(
        current_app.config['DM_HTTP_PROTO'],
        current_app.config['DM_MAIN_SERVER_NAME'],
        token,
        quote_plus(user['users']['emailAddress'])))


@main.route('/suppliers/<int:supplier_code>/move-existing-user', methods=['POST'])
@login_required
@role_required('admin')
def move_user_to_new_supplier(supplier_code):
    move_user_form = MoveUserForm(request.form)
    new_seller_user_form = NewSellerUserForm(request.form)
    try:
        suppliers = data_api_client.get_supplier(supplier_code)
        users = data_api_client.find_users(supplier_code)
    except HTTPError as e:
        current_app.logger.error(str(e), supplier_code)
        if e.status_code != 404:
            raise
        else:
            abort(404, "Supplier not found")

    if move_user_form.validate():
        try:
            user = data_api_client.get_user(email_address=move_user_form.user_to_move_email_address.data)
        except HTTPError as e:
            current_app.logger.error(str(e), supplier_code)
            raise

        if user:
            data_api_client.update_user(
                user['users']['id'],
                role='supplier',
                supplier_code=supplier_code,
                active=True,
                updater=current_user.email_address
            )
            flash("user_moved", "success")
        else:
            flash("user_not_moved", "error")
        return redirect(url_for('.find_supplier_users', supplier_code=supplier_code))
    else:
        return render_template_with_csrf(
            "view_supplier_users.html",
            status_code=400,
            invite_form=InviteForm(),
            move_user_form=move_user_form,
            new_seller_user_form=new_seller_user_form,
            users=users["users"],
            supplier=suppliers['supplier']
        )


@main.route('/suppliers/services', methods=['GET'])
@login_required
@role_required('admin', 'admin-ccs-category')
def find_supplier_services():
    if not request.args.get('supplier_code'):
        abort(404)

    supplier_code = int(request.args['supplier_code'])
    supplier = data_api_client.get_supplier(supplier_code)
    services = data_api_client.find_services(supplier_code)
    evidence = data_api_client.req.evidence().all().get(params={'supplier_code': supplier_code})['evidence']

    if 'domains' not in supplier['supplier']:
        domains = {}
        supplier['supplier']['domains'] = domains
    else:
        domains = supplier['supplier']['domains']

    assessed = [sd for sd in domains.get('all', []) if sd['status'] == 'assessed']
    for a in assessed:
        pricing = supplier['supplier'].get('pricing', None)
        if pricing:
            price = pricing.get(a['domain_name'], None)
            if price:
                a['price'] = price['maxPrice']
        else:
            a['price'] = 'Not specified'

    for e in evidence:
        if 'submitted_at' in e and e['submitted_at']:
            e['submitted_at'] = pendulum.parse(e['submitted_at']).format('%d-%m-%Y')
        if 'rejected_at' in e and e['rejected_at']:
            e['rejected_at'] = pendulum.parse(e['rejected_at']).format('%d-%m-%Y')
        if 'approved_at' in e and e['approved_at']:
            e['approved_at'] = pendulum.parse(e['approved_at']).format('%d-%m-%Y')
        if 'created_at' in e and e['created_at']:
            e['created_at'] = pendulum.parse(e['created_at']).format('%d-%m-%Y')
    assessments_draft = [e for e in evidence if e['status'] == 'draft']
    assessments_rejected = [e for e in evidence if e['status'] == 'rejected']
    assessments_approved = [e for e in evidence if e['status'] == 'assessed']
    assessments_submitted = [e for e in evidence if e['status'] == 'submitted']

    return render_template_with_csrf(
        "view_supplier_services.html",
        services=services["services"],
        supplier=supplier["supplier"],
        assessed=assessed,
        assessments_draft=assessments_draft,
        assessments_rejected=assessments_rejected,
        assessments_approved=assessments_approved,
        assessments_submitted=assessments_submitted
    )


@main.route('/suppliers/<int:supplier_code>', methods=['POST'])
@login_required
@role_required('admin')
def update_supplier_domain_price_status(supplier_code):
    if 'supplier_domain_id' in request.args:
        supplier_domain_id = int(request.args['supplier_domain_id'])
        price_status = request.args['price_status']
        (
            data_api_client
            .req
            .suppliers(supplier_code)
            .domain(supplier_domain_id)
            .post({
                'update_details': {
                    'updated_by': current_user.email_address
                },
                'price_status': price_status
            })
        )

    return redirect(url_for('.find_supplier_services', supplier_code=supplier_code))


@main.route('/suppliers/<int:supplier_code>/invite-user', methods=['POST'])
@login_required
@role_required('admin')
def invite_user(supplier_code):
    invite_form = InviteForm(request.form)
    new_seller_user_form = NewSellerUserForm(request.form)
    try:
        supplier = data_api_client.get_supplier(supplier_code)['supplier']
        users = data_api_client.find_users(supplier_code)
    except HTTPError as e:
        current_app.logger.error(str(e), supplier_code)
        if e.status_code != 404:
            raise
        else:
            abort(404, "Supplier not found")

    if invite_form.validate():
        email_address = invite_form.email_address.data
        user_name = invite_form.name.data
        data = {
            'name': user_name,
            'emailAddress': email_address,
            'supplierCode': supplier_code,
            'supplierName': supplier['name'],
        }
        token = generate_token(data, current_app.config['SECRET_KEY'], current_app.config['INVITE_EMAIL_SALT'])

        url = '{}://{}/{}/{}'.format(
            current_app.config['DM_HTTP_PROTO'],
            current_app.config['DM_MAIN_SERVER_NAME'],
            current_app.config['CREATE_USER_PATH'],
            format(token)
        )

        email_body = render_template(
            'emails/invite_user_email.html',
            url=url,
            supplier=supplier['name'],
            name=user_name,
        )

        try:
            send_email(
                email_address,
                email_body,
                current_app.config['INVITE_EMAIL_SUBJECT'],
                current_app.config['INVITE_EMAIL_FROM'],
                current_app.config['INVITE_EMAIL_NAME'],
            )
        except EmailError as e:
            current_app.logger.error(
                'Invitation email failed to send error {} to {} supplier {} supplier code {} '.format(
                    str(e),
                    email_address,
                    current_user.supplier_name,
                    current_user.supplier_code)
            )
            abort(503, "Failed to send user invite reset")

        try:
            data_api_client.record_supplier_invite(
                supplier_code=supplier_code,
                email_address=email_address
            )
        except APIError as e:
            current_app.logger.warning('Could not record supplier invite for {}: {}'.format(e.message, email_address))

        flash('user_invited', 'success')
        return redirect(url_for('.find_supplier_users', supplier_code=supplier_code))
    else:
        return render_template_with_csrf(
            "view_supplier_users.html",
            status_code=400,
            invite_form=invite_form,
            new_seller_user_form=new_seller_user_form,
            move_user_form=MoveUserForm(),
            users=users["users"],
            supplier=supplier
        )


@main.route('/suppliers/<int:supplier_code>/add-new-supplier-user', methods=['POST'])
@login_required
@role_required('admin')
def add_new_supplier_user(supplier_code):
    invite_form = InviteForm(request.form)
    new_seller_user_form = NewSellerUserForm(request.form)
    supplier = data_api_client.get_supplier(supplier_code)['supplier']
    if not new_seller_user_form.validate():
        users = data_api_client.find_users(supplier_code)
        return render_template_with_csrf(
            "view_supplier_users.html",
            new_seller_user_form=new_seller_user_form,
            move_user_form=MoveUserForm(),
            invite_form=invite_form,
            supplier=supplier,
            users=users["users"],
        )
    try:
        user = data_api_client.create_user({
            'name': new_seller_user_form.new_name.data,
            'password': new_seller_user_form.new_phone.data,
            'emailAddress': new_seller_user_form.new_email_address.data,
            'role': 'supplier',
            'supplierCode': supplier_code
        })
    except HTTPError as e:
        current_app.logger.error(str(e), supplier_code)
        if e.status_code != 404:
            raise
        else:
            abort(404, "Supplier not found")

    users = data_api_client.find_users(supplier_code)
    return render_template_with_csrf(
            "view_supplier_users.html",
            new_seller_user_form=NewSellerUserForm(),
            move_user_form=MoveUserForm(),
            invite_form=invite_form,
            supplier=supplier,
            users=users["users"],
    )


@main.route('/suppliers/assessments/trigger', methods=['POST'])
@login_required
@role_required('admin')
def trigger_assessment():
    """Triggers a domain assessment for a supplier."""

    data_api_client.req.assessments().post(data={
        'assessment': {
            'brief_id': request.form['brief_id'],
            'domain_name': request.form['domain_name'],
            'supplier_code': request.form['supplier_code']
        },
        'update_details': {
            'updated_by': ''
        }
    })

    return redirect(url_for('.assessments_review'))


@main.route('/supplier/<int:supplier_code>/full', methods=['GET'])
@login_required
@role_required('admin')
def full_supplier_view(supplier_code):
    supplier = data_api_client.get_supplier(supplier_code)['supplier']

    props = {}
    props['application'] = dict(supplier)
    props['application']['case_study_url'] = '{}://{}/case-study/'.format(
        current_app.config['DM_HTTP_PROTO'],
        current_app.config['DM_MAIN_SERVER_NAME']
    )
    rendered_component = render_component('bundles/SellerRegistration/ApplicationPreviewWidget.js', props)

    return render_template(
        '_react.html',
        component=rendered_component
    )
