from flask import render_template, request, redirect, url_for, abort, current_app
from flask_login import login_required, current_user, flash
from dateutil.parser import parse as parse_date

from .. import main
from ... import data_api_client, content_loader
from ..forms import EmailAddressForm
from ..auth import role_required
from dmapiclient import HTTPError, APIError
from dmapiclient.audit import AuditTypes
from dmutils.email import send_email, generate_token, MandrillException
from dmutils.documents import (
    get_signed_url, get_agreement_document_path, file_is_pdf,
    AGREEMENT_FILENAME, SIGNED_AGREEMENT_PREFIX, COUNTERSIGNED_AGREEMENT_FILENAME,
)
from dmutils import s3
from dmutils.formats import datetimeformat


@main.route('/suppliers', methods=['GET'])
@login_required
@role_required('admin', 'admin-ccs-category', 'admin-ccs-sourcing')
def find_suppliers():
    suppliers = data_api_client.find_suppliers(
        prefix=request.args.get("supplier_name_prefix"),
        duns_number=request.args.get("supplier_duns_number")
    )

    return render_template(
        "view_suppliers.html",
        suppliers=suppliers['suppliers'],
        signed_agreement_prefix=SIGNED_AGREEMENT_PREFIX,
        agreement_prefix=AGREEMENT_FILENAME
    )


@main.route('/suppliers/<string:supplier_id>/edit/name', methods=['GET'])
@login_required
@role_required('admin')
def edit_supplier_name(supplier_id):
    supplier = data_api_client.get_supplier(supplier_id)

    return render_template(
        "edit_supplier_name.html",
        supplier=supplier["suppliers"]
    )


@main.route('/suppliers/<string:supplier_id>/edit/declarations/<string:framework_slug>', methods=['GET'])
@login_required
@role_required('admin-ccs-sourcing')
def view_supplier_declaration(supplier_id, framework_slug):
    supplier = data_api_client.get_supplier(supplier_id)['suppliers']
    framework = data_api_client.get_framework(framework_slug)['frameworks']
    if framework['status'] not in ['pending', 'standstill', 'live']:
        abort(403)
    try:
        declaration = data_api_client.get_supplier_declaration(supplier_id, framework_slug)['declaration']
    except APIError as e:
        if e.status_code != 404:
            raise
        declaration = {}

    content = content_loader.get_builder(framework_slug, 'declaration').filter(declaration)

    return render_template(
        "suppliers/view_declaration.html",
        supplier=supplier,
        framework=framework,
        declaration=declaration,
        content=content
    )


@main.route('/suppliers/<supplier_id>/agreements/<framework_slug>/<document_name>', methods=['GET'])
@login_required
@role_required('admin', 'admin-ccs-sourcing')
def download_agreement_file(supplier_id, framework_slug, document_name):
    supplier_framework = data_api_client.get_supplier_framework_info(supplier_id, framework_slug)['frameworkInterest']
    if not supplier_framework.get('declaration'):
        abort(404)
    agreements_bucket = s3.S3(current_app.config['DM_AGREEMENTS_BUCKET'])
    prefix = get_agreement_document_path(framework_slug, supplier_id, document_name)
    agreement_documents = agreements_bucket.list(prefix=prefix)
    if not len(agreement_documents):
        abort(404)
    path = agreement_documents[-1]['path']
    url = get_signed_url(agreements_bucket, path, current_app.config['DM_ASSETS_URL'])
    if not url:
        abort(404)

    return redirect(url)


@main.route('/suppliers/<supplier_id>/countersigned-agreements/<framework_slug>',
            methods=['GET'])
@login_required
@role_required('admin-ccs-sourcing')
def list_countersigned_agreement_file(supplier_id, framework_slug):
    supplier = data_api_client.get_supplier(supplier_id)['suppliers']
    framework = data_api_client.get_framework(framework_slug)['frameworks']
    agreements_bucket = s3.S3(current_app.config['DM_AGREEMENTS_BUCKET'])
    path = get_agreement_document_path(framework_slug, supplier_id, COUNTERSIGNED_AGREEMENT_FILENAME)
    countersigned_agreement_document = agreements_bucket.get_key(path)
    if countersigned_agreement_document:
        countersigned_agreement = countersigned_agreement_document
        countersigned_agreement['last_modified'] = datetimeformat(parse_date(
            countersigned_agreement['last_modified']))
        countersigned_agreement = [countersigned_agreement]
    else:
        countersigned_agreement = []

    return render_template(
        "suppliers/upload_countersigned_agreement.html",
        supplier=supplier,
        framework=framework,
        countersigned_agreement=countersigned_agreement,
        countersigned_agreement_filename=COUNTERSIGNED_AGREEMENT_FILENAME
    )


@main.route('/suppliers/<supplier_id>/countersigned-agreements/<framework_slug>', methods=['POST'])
@login_required
@role_required('admin-ccs-sourcing')
def upload_countersigned_agreement_file(supplier_id, framework_slug):
    agreements_bucket = s3.S3(current_app.config['DM_AGREEMENTS_BUCKET'])
    errors = {}

    if request.files.get('countersigned_agreement'):
        the_file = request.files['countersigned_agreement']
        if not file_is_pdf(the_file):
            errors['countersigned_agreement'] = 'not_pdf'

        if 'countersigned_agreement' not in errors.keys():
            filename = get_agreement_document_path(framework_slug, supplier_id, COUNTERSIGNED_AGREEMENT_FILENAME)
            agreements_bucket.save(filename, the_file)

            data_api_client.create_audit_event(
                audit_type=AuditTypes.upload_countersigned_agreement,
                user=current_user.email_address,
                object_type='suppliers',
                object_id=supplier_id,
                data={'upload_countersigned_agreement': filename})

            flash('countersigned_agreement', 'upload_countersigned_agreement')

    if len(errors) > 0:
        for category, message in errors.items():
            flash(category, message)

    return redirect(url_for(
        '.list_countersigned_agreement_file',
        supplier_id=supplier_id,
        framework_slug=framework_slug)
    )


@main.route('/suppliers/<supplier_id>/countersigned-agreements-remove/<framework_slug>',
            methods=['GET', 'POST'])
@login_required
@role_required('admin-ccs-sourcing')
def remove_countersigned_agreement_file(supplier_id, framework_slug):
    agreements_bucket = s3.S3(current_app.config['DM_AGREEMENTS_BUCKET'])
    document = get_agreement_document_path(framework_slug, supplier_id, COUNTERSIGNED_AGREEMENT_FILENAME)

    if request.method == 'GET':
        flash('countersigned_agreement', 'remove_countersigned_agreement')

    if request.method == 'POST':
        agreements_bucket.delete_key(document)

        data_api_client.create_audit_event(
            audit_type=AuditTypes.delete_countersigned_agreement,
            user=current_user.email_address,
            object_type='suppliers',
            object_id=supplier_id,
            data={'upload_countersigned_agreement': document})

    return redirect(url_for(
        '.list_countersigned_agreement_file',
        supplier_id=supplier_id,
        framework_slug=framework_slug)
    )


@main.route(
    '/suppliers/<string:supplier_id>/edit/declarations/<string:framework_slug>/<string:section_id>',
    methods=['GET'])
@login_required
@role_required('admin-ccs-sourcing')
def edit_supplier_declaration_section(supplier_id, framework_slug, section_id):
    supplier = data_api_client.get_supplier(supplier_id)['suppliers']
    framework = data_api_client.get_framework(framework_slug)['frameworks']
    if framework['status'] not in ['pending', 'standstill', 'live']:
        abort(403)
    try:
        declaration = data_api_client.get_supplier_declaration(supplier_id, framework_slug)['declaration']
    except APIError as e:
        if e.status_code != 404:
            raise
        declaration = {}

    content = content_loader.get_builder(framework_slug, 'declaration').filter(declaration)
    section = content.get_section(section_id)
    if section is None:
        abort(404)

    return render_template(
        "suppliers/edit_declaration.html",
        supplier=supplier,
        framework=framework,
        declaration=declaration,
        section=section
    )


@main.route(
    '/suppliers/<string:supplier_id>/edit/declarations/<string:framework_slug>/<string:section_id>',
    methods=['POST'])
def update_supplier_declaration_section(supplier_id, framework_slug, section_id):
    supplier = data_api_client.get_supplier(supplier_id)['suppliers']
    framework = data_api_client.get_framework(framework_slug)['frameworks']
    if framework['status'] not in ['pending', 'standstill', 'live']:
        abort(403)
    try:
        declaration = data_api_client.get_supplier_declaration(supplier_id, framework_slug)['declaration']
    except APIError as e:
        if e.status_code != 404:
            raise
        declaration = {}

    content = content_loader.get_builder(framework_slug, 'declaration').filter(declaration)
    section = content.get_section(section_id)
    if section is None:
        abort(404)

    posted_data = section.get_data(request.form)

    if section.has_changes_to_save(declaration, posted_data):
        declaration.update(posted_data)
        data_api_client.set_supplier_declaration(
            supplier_id, framework_slug, declaration,
            current_user.email_address)

    return redirect(url_for('.view_supplier_declaration',
                            supplier_id=supplier_id, framework_slug=framework_slug))


@main.route('/suppliers/<string:supplier_id>/edit/name', methods=['POST'])
@login_required
@role_required('admin')
def update_supplier_name(supplier_id):
    supplier = data_api_client.get_supplier(supplier_id)
    new_supplier_name = request.form.get('new_supplier_name', '')

    data_api_client.update_supplier(
        supplier['suppliers']['id'], {'name': new_supplier_name}, current_user.email_address
    )

    return redirect(url_for('.find_suppliers', supplier_name_prefix=new_supplier_name[:1]))


@main.route('/suppliers/users', methods=['GET'])
@login_required
@role_required('admin', 'admin-ccs-category')
def find_supplier_users():
    form = EmailAddressForm()

    if not request.args.get('supplier_id'):
        abort(404)

    supplier = data_api_client.get_supplier(request.args['supplier_id'])
    users = data_api_client.find_users(request.args.get("supplier_id"))

    return render_template(
        "view_supplier_users.html",
        users=users["users"],
        form=form,
        supplier=supplier["suppliers"]
    )


@main.route('/suppliers/users/<int:user_id>/unlock', methods=['POST'])
@login_required
@role_required('admin')
def unlock_user(user_id):
    user = data_api_client.update_user(user_id, locked=False, updater=current_user.email_address)
    if "source" in request.form:
        return redirect(request.form["source"])
    return redirect(url_for('.find_supplier_users', supplier_id=user['users']['supplier']['supplierId']))


@main.route('/suppliers/users/<int:user_id>/activate', methods=['POST'])
@login_required
@role_required('admin')
def activate_user(user_id):
    user = data_api_client.update_user(user_id, active=True, updater=current_user.email_address)
    if "source" in request.form:
        return redirect(request.form["source"])
    return redirect(url_for('.find_supplier_users', supplier_id=user['users']['supplier']['supplierId']))


@main.route('/suppliers/users/<int:user_id>/deactivate', methods=['POST'])
@login_required
@role_required('admin')
def deactivate_user(user_id):
    user = data_api_client.update_user(user_id, active=False, updater=current_user.email_address)
    if "source" in request.form:
        return redirect(request.form["source"])
    return redirect(url_for('.find_supplier_users', supplier_id=user['users']['supplier']['supplierId']))


@main.route('/suppliers/users/<int:user_id>/remove-from-supplier', methods=['POST'])
@login_required
@role_required('admin')
def remove_from_supplier(user_id):
    data_api_client.update_user(user_id, role='buyer', updater=current_user.email_address)
    return redirect(url_for('.find_supplier_users', supplier_id=request.form['supplier_id']))


@main.route('/suppliers/services', methods=['GET'])
@login_required
@role_required('admin', 'admin-ccs-category')
def find_supplier_services():

    if not request.args.get('supplier_id'):
        abort(404)

    supplier = data_api_client.get_supplier(request.args['supplier_id'])
    services = data_api_client.find_services(request.args.get("supplier_id"))

    return render_template(
        "view_supplier_services.html",
        services=services["services"],
        supplier=supplier["suppliers"]
    )


@main.route('/suppliers/<int:supplier_id>/invite-user', methods=['POST'])
@login_required
@role_required('admin')
def invite_user(supplier_id):
    form = EmailAddressForm()

    try:
        suppliers = data_api_client.get_supplier(supplier_id)
        users = data_api_client.find_users(supplier_id)
    except HTTPError as e:
        current_app.logger.error(str(e), supplier_id)
        if e.status_code != 404:
            raise
        else:
            abort(404, "Supplier not found")

    if form.validate_on_submit():
        token = generate_token(
            {
                "supplier_id": supplier_id,
                "supplier_name": suppliers['suppliers']['name'],
                "email_address": form.email_address.data
            },
            current_app.config['SHARED_EMAIL_KEY'],
            current_app.config['INVITE_EMAIL_SALT']
        )

        url = "{}{}/{}".format(
            request.url_root,
            current_app.config['CREATE_USER_PATH'],
            format(token)
        )

        email_body = render_template(
            "emails/invite_user_email.html",
            url=url,
            supplier=suppliers['suppliers']['name'])

        try:
            send_email(
                form.email_address.data,
                email_body,
                current_app.config['DM_MANDRILL_API_KEY'],
                current_app.config['INVITE_EMAIL_SUBJECT'],
                current_app.config['INVITE_EMAIL_FROM'],
                current_app.config['INVITE_EMAIL_NAME'],
                ["user-invite"]
            )
        except MandrillException as e:
            current_app.logger.error(
                "Invitation email failed to send error {} to {} supplier {} supplier id {} ".format(
                    str(e),
                    form.email_address.data,
                    current_user.supplier_name,
                    current_user.supplier_id)
            )
            abort(503, "Failed to send user invite reset")

        data_api_client.create_audit_event(
            audit_type=AuditTypes.invite_user,
            user=current_user.email_address,
            object_type='suppliers',
            object_id=supplier_id,
            data={'invitedEmail': form.email_address.data})

        flash('user_invited', 'success')
        return redirect(url_for('.find_supplier_users', supplier_id=supplier_id))
    else:
        return render_template(
            "view_supplier_users.html",
            form=form,
            users=users["users"],
            supplier=suppliers["suppliers"]
        ), 400
