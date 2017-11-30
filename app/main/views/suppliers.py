from collections import OrderedDict
from itertools import groupby
from operator import itemgetter

from dateutil.parser import parse as parse_date
from dmapiclient import HTTPError, APIError
from dmapiclient.audit import AuditTypes
from dmutils import s3
from dmutils.documents import (
    AGREEMENT_FILENAME, COUNTERPART_FILENAME,
    file_is_pdf, get_document_path, get_extension, get_signed_url,
    generate_timestamped_document_upload_path, degenerate_document_path_and_return_doc_name,
    generate_download_filename)
from dmutils.email import send_user_account_email
from dmutils.formats import datetimeformat
from flask import render_template, request, redirect, url_for, abort, current_app
from flask_login import current_user, flash

from .. import main
from ..auth import role_required
from ..forms import EmailAddressForm, MoveUserForm
from ... import data_api_client, content_loader


@main.route('/suppliers', methods=['GET'])
@role_required('admin', 'admin-ccs-category', 'admin-ccs-sourcing', 'admin-framework-manager')
def find_suppliers():
    if request.args.get("supplier_id"):
        suppliers = [data_api_client.get_supplier(request.args.get("supplier_id"))['suppliers']]
    else:
        suppliers = data_api_client.find_suppliers(
            prefix=request.args.get("supplier_name_prefix"),
            duns_number=request.args.get("supplier_duns_number")
        )['suppliers']

    return render_template(
        "view_suppliers.html",
        suppliers=suppliers,
        agreement_filename=AGREEMENT_FILENAME
    )


@main.route('/suppliers/<string:supplier_id>/edit/name', methods=['GET'])
@role_required('admin', 'admin-ccs-category')
def edit_supplier_name(supplier_id):
    supplier = data_api_client.get_supplier(supplier_id)

    return render_template(
        "edit_supplier_name.html",
        supplier=supplier["suppliers"]
    )


@main.route('/suppliers/<string:supplier_id>/edit/name', methods=['POST'])
@role_required('admin', 'admin-ccs-category')
def update_supplier_name(supplier_id):
    supplier = data_api_client.get_supplier(supplier_id)
    new_supplier_name = request.form.get('new_supplier_name', '')

    data_api_client.update_supplier(
        supplier['suppliers']['id'], {'name': new_supplier_name}, current_user.email_address
    )

    return redirect(url_for('.find_suppliers', supplier_id=supplier_id))


@main.route('/suppliers/<string:supplier_id>/edit/declarations/<string:framework_slug>', methods=['GET'])
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

    content = content_loader.get_manifest(framework_slug, 'declaration').filter(declaration)

    return render_template(
        "suppliers/view_declaration.html",
        supplier=supplier,
        framework=framework,
        declaration=declaration,
        content=content
    )


@main.route('/suppliers/<supplier_id>/agreements/<framework_slug>', methods=['GET'])
@role_required('admin-ccs-sourcing', 'admin-framework-manager')
def view_signed_agreement(supplier_id, framework_slug):
    # not properly validating this - all we do is pass it through
    next_status = request.args.get("next_status")

    supplier = data_api_client.get_supplier(supplier_id)['suppliers']
    framework = data_api_client.get_framework(framework_slug)['frameworks']
    if not framework.get('frameworkAgreementVersion'):
        abort(404)
    supplier_framework = data_api_client.get_supplier_framework_info(supplier_id, framework_slug)['frameworkInterest']
    if not supplier_framework.get('agreementReturned'):
        abort(404)

    if framework["status"] in ("live", "expired"):
        # If the framework is live or expired we don't need to filter drafts, we only care about successful services
        service_iterator = data_api_client.find_services_iter(supplier_id=supplier_id, framework=framework_slug)
        lot_slugs_names = [(service["lotSlug"], service["lotName"]) for service in service_iterator]
    else:
        # If the framework has not yet become live we need to filter out unsuccessful services
        service_iterator = data_api_client.find_draft_services_iter(supplier_id=supplier_id, framework=framework_slug)
        lot_slugs_names = [
            (service["lotSlug"], service["lotName"]) for service in service_iterator if service["status"] == "submitted"
        ]

    agreements_bucket = s3.S3(current_app.config['DM_AGREEMENTS_BUCKET'])
    path = supplier_framework['agreementPath']
    url = get_signed_url(agreements_bucket, path, current_app.config['DM_ASSETS_URL'])
    if not url:
        abort(404)
    return render_template(
        "suppliers/view_signed_agreement.html",
        supplier=supplier,
        framework=framework,
        supplier_framework=supplier_framework,
        lot_slugs_names=OrderedDict(sorted(lot_slugs_names)),
        agreement_url=url,
        agreement_ext=get_extension(path),
        next_status=next_status,
    )


@main.route('/suppliers/agreements/<agreement_id>/on-hold', methods=['POST'])
@role_required('admin-ccs-sourcing')
def put_signed_agreement_on_hold(agreement_id):
    # not properly validating this - all we do is pass it through
    next_status = request.args.get("next_status")

    agreement = data_api_client.put_signed_agreement_on_hold(agreement_id, current_user.email_address)["agreement"]

    organisation = request.form['nameOfOrganisation']
    flash(u'The agreement for {} was put on hold.'.format(organisation), 'message')

    return redirect(url_for(
        '.next_agreement',
        framework_slug=agreement["frameworkSlug"],
        supplier_id=agreement["supplierId"],
        status=next_status,
    ))


@main.route('/suppliers/agreements/<agreement_id>/approve', methods=['POST'])
@role_required('admin-ccs-sourcing')
def approve_agreement_for_countersignature(agreement_id):
    # not properly validating this - all we do is pass it through
    next_status = request.args.get("next_status")

    agreement = data_api_client.approve_agreement_for_countersignature(
        agreement_id,
        current_user.email_address,
        current_user.id,
    )["agreement"]
    organisation = request.form['nameOfOrganisation']
    flash(u'The agreement for {} was approved. They will receive a countersigned version soon.'
          .format(organisation), 'message')

    return redirect(url_for(
        '.next_agreement',
        framework_slug=agreement["frameworkSlug"],
        supplier_id=agreement["supplierId"],
        status=next_status,
    ))


@main.route('/suppliers/agreements/<agreement_id>/unapprove', methods=['POST'])
@role_required('admin-ccs-sourcing')
def unapprove_agreement_for_countersignature(agreement_id):
    # not properly validating this - all we do is pass it through
    next_status = request.args.get("next_status")

    agreement = data_api_client.unapprove_agreement_for_countersignature(
        agreement_id,
        current_user.email_address,
        current_user.id,
    )["agreement"]
    organisation = request.form['nameOfOrganisation']
    flash(u'The agreement for {} had its approval cancelled. You can approve it again at any time.'
          .format(organisation), 'message')

    return redirect(url_for(
        '.view_signed_agreement',
        framework_slug=agreement["frameworkSlug"],
        supplier_id=agreement["supplierId"],
        next_status=next_status,
    ))


@main.route('/suppliers/<supplier_id>/agreement/<framework_slug>', methods=['GET'])
@role_required('admin-ccs-sourcing', 'admin-framework-manager')
def download_signed_agreement_file(supplier_id, framework_slug):
    # This route is used for pre-G-Cloud-8 agreement document downloads
    supplier_framework = data_api_client.get_supplier_framework_info(supplier_id, framework_slug)['frameworkInterest']
    document_name = degenerate_document_path_and_return_doc_name(supplier_framework['agreementPath'])
    return download_agreement_file(supplier_id, framework_slug, document_name)


@main.route('/suppliers/<supplier_id>/agreements/<framework_slug>/<document_name>', methods=['GET'])
@role_required('admin-ccs-sourcing', 'admin-framework-manager')
def download_agreement_file(supplier_id, framework_slug, document_name):
    supplier_framework = data_api_client.get_supplier_framework_info(supplier_id, framework_slug)['frameworkInterest']
    if supplier_framework is None or not supplier_framework.get("declaration"):
        abort(404)

    agreements_bucket = s3.S3(current_app.config['DM_AGREEMENTS_BUCKET'])
    path = get_document_path(framework_slug, supplier_id, 'agreements', document_name)
    url = get_signed_url(agreements_bucket, path, current_app.config['DM_ASSETS_URL'])
    if not url:
        abort(404)

    return redirect(url)


@main.route('/suppliers/<supplier_id>/countersigned-agreements/<framework_slug>', methods=['GET'])
@role_required('admin-ccs-sourcing')
def list_countersigned_agreement_file(supplier_id, framework_slug):
    supplier = data_api_client.get_supplier(supplier_id)['suppliers']
    framework = data_api_client.get_framework(framework_slug)['frameworks']
    supplier_framework = data_api_client.get_supplier_framework_info(supplier_id, framework_slug)['frameworkInterest']
    if not supplier_framework['onFramework'] or supplier_framework['agreementStatus'] in (None, 'draft'):
        abort(404)
    agreements_bucket = s3.S3(current_app.config['DM_AGREEMENTS_BUCKET'])
    countersigned_agreement_document = agreements_bucket.get_key(supplier_framework.get('countersignedPath'))

    countersigned_agreement = []
    if countersigned_agreement_document:
        last_modified = datetimeformat(parse_date(countersigned_agreement_document['last_modified']))
        document_name = degenerate_document_path_and_return_doc_name(supplier_framework.get('countersignedPath'))
        countersigned_agreement = [{"last_modified": last_modified, "document_name": document_name}]

    return render_template(
        "suppliers/upload_countersigned_agreement.html",
        supplier=supplier,
        framework=framework,
        countersigned_agreement=countersigned_agreement
    )


@main.route('/suppliers/<supplier_id>/countersigned-agreements/<framework_slug>', methods=['POST'])
@role_required('admin-ccs-sourcing')
def upload_countersigned_agreement_file(supplier_id, framework_slug):
    supplier_framework = data_api_client.get_supplier_framework_info(supplier_id, framework_slug)['frameworkInterest']
    if not supplier_framework['onFramework'] or supplier_framework['agreementStatus'] in (None, 'draft'):
        abort(404)
    agreement_id = supplier_framework['agreementId']
    agreements_bucket = s3.S3(current_app.config['DM_AGREEMENTS_BUCKET'])
    errors = {}

    if request.files.get('countersigned_agreement'):
        the_file = request.files['countersigned_agreement']
        if not file_is_pdf(the_file):
            errors['countersigned_agreement'] = 'not_pdf'

        if 'countersigned_agreement' not in errors.keys():
            supplier_name = supplier_framework.get('declaration', {}).get('nameOfOrganisation')
            if not supplier_name:
                supplier_name = data_api_client.get_supplier(supplier_id)['suppliers']['name']
            if supplier_framework['agreementStatus'] not in ['approved', 'countersigned']:
                data_api_client.approve_agreement_for_countersignature(
                    agreement_id,
                    current_user.email_address,
                    current_user.id
                )

            path = generate_timestamped_document_upload_path(
                framework_slug, supplier_id, 'agreements', COUNTERPART_FILENAME
            )
            download_filename = generate_download_filename(supplier_id, COUNTERPART_FILENAME, supplier_name)
            agreements_bucket.save(path, the_file, acl='private', move_prefix=None, download_filename=download_filename)

            data_api_client.update_framework_agreement(
                agreement_id,
                {"countersignedAgreementPath": path},
                current_user.email_address
            )

            data_api_client.create_audit_event(
                audit_type=AuditTypes.upload_countersigned_agreement,
                user=current_user.email_address,
                object_type='suppliers',
                object_id=supplier_id,
                data={'upload_countersigned_agreement': path})

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
@role_required('admin-ccs-sourcing')
def remove_countersigned_agreement_file(supplier_id, framework_slug):
    supplier_framework = data_api_client.get_supplier_framework_info(supplier_id, framework_slug)['frameworkInterest']
    document = supplier_framework.get('countersignedPath')
    agreements_bucket = s3.S3(current_app.config['DM_AGREEMENTS_BUCKET'])

    if request.method == 'GET':
        flash('countersigned_agreement', 'remove_countersigned_agreement')

    if request.method == 'POST':
        # Remove path first - as we don't want path to exist in DB with no corresponding file in S3
        # But an orphaned file in S3 wouldn't be so bad
        data_api_client.update_framework_agreement(
            supplier_framework['agreementId'],
            {"countersignedAgreementPath": None},
            current_user.email_address
        )
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

    content = content_loader.get_manifest(framework_slug, 'declaration').filter(declaration)
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
@role_required('admin-ccs-sourcing')
def update_supplier_declaration_section(supplier_id, framework_slug, section_id):
    # Supplier must exist.
    data_api_client.get_supplier(supplier_id)
    framework = data_api_client.get_framework(framework_slug)['frameworks']
    if framework['status'] not in ['pending', 'standstill', 'live']:
        abort(403)
    try:
        declaration = data_api_client.get_supplier_declaration(supplier_id, framework_slug)['declaration']
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
            supplier_id, framework_slug, declaration,
            current_user.email_address)

    return redirect(url_for('.view_supplier_declaration',
                            supplier_id=supplier_id, framework_slug=framework_slug))


@main.route('/suppliers/users', methods=['GET'])
@role_required('admin', 'admin-ccs-category', 'admin-framework-manager')
def find_supplier_users():

    if not request.args.get('supplier_id'):
        abort(404)

    supplier = data_api_client.get_supplier(request.args['supplier_id'])
    users = data_api_client.find_users(request.args.get("supplier_id"))

    return render_template(
        "view_supplier_users.html",
        users=users["users"],
        invite_form=EmailAddressForm(),
        move_user_form=MoveUserForm(),
        supplier=supplier["suppliers"]
    )


@main.route('/suppliers/users/<int:user_id>/unlock', methods=['POST'])
@role_required('admin')
def unlock_user(user_id):
    user = data_api_client.update_user(user_id, locked=False, updater=current_user.email_address)
    if "source" in request.form:
        return redirect(request.form["source"])
    return redirect(url_for('.find_supplier_users', supplier_id=user['users']['supplier']['supplierId']))


@main.route('/suppliers/users/<int:user_id>/activate', methods=['POST'])
@role_required('admin')
def activate_user(user_id):
    user = data_api_client.update_user(user_id, active=True, updater=current_user.email_address)
    if "source" in request.form:
        return redirect(request.form["source"])
    return redirect(url_for('.find_supplier_users', supplier_id=user['users']['supplier']['supplierId']))


@main.route('/suppliers/users/<int:user_id>/deactivate', methods=['POST'])
@role_required('admin')
def deactivate_user(user_id):
    user = data_api_client.update_user(user_id, active=False, updater=current_user.email_address)
    if "source" in request.form:
        return redirect(request.form["source"])
    return redirect(url_for('.find_supplier_users', supplier_id=user['users']['supplier']['supplierId']))


@main.route('/suppliers/<int:supplier_id>/move-existing-user', methods=['POST'])
@role_required('admin')
def move_user_to_new_supplier(supplier_id):
    move_user_form = MoveUserForm()

    try:
        suppliers = data_api_client.get_supplier(supplier_id)
        users = data_api_client.find_users(supplier_id)
    except HTTPError as e:
        current_app.logger.error(str(e), supplier_id)
        if e.status_code != 404:
            raise
        else:
            abort(404, "Supplier not found")

    if move_user_form.validate_on_submit():
        try:
            user = data_api_client.get_user(email_address=move_user_form.user_to_move_email_address.data)
        except HTTPError as e:
            current_app.logger.error(str(e), supplier_id)
            raise

        if user:
            data_api_client.update_user(
                user['users']['id'],
                role='supplier',
                supplier_id=supplier_id,
                active=True,
                updater=current_user.email_address
            )
            flash("user_moved", "success")
        else:
            flash("user_not_moved", "error")
        return redirect(url_for('.find_supplier_users', supplier_id=supplier_id))
    else:
        return render_template(
            "view_supplier_users.html",
            invite_form=EmailAddressForm(),
            move_user_form=move_user_form,
            users=users["users"],
            supplier=suppliers["suppliers"]
        ), 400


@main.route('/suppliers/<int:supplier_id>/services', methods=['GET'])
@role_required('admin-ccs-category', 'admin-framework-manager')
def find_supplier_services(supplier_id):
    remove_services_for_framework_slug = request.args.get('remove', None)

    frameworks = data_api_client.find_frameworks()['frameworks']
    supplier = data_api_client.get_supplier(supplier_id)["suppliers"]
    services = data_api_client.find_services(supplier_id)['services']

    frameworks_services = {
        framework_slug: list(framework_services)
        for framework_slug, framework_services in
        groupby(sorted(services, key=itemgetter('frameworkSlug')), key=itemgetter('frameworkSlug'))
    }

    if remove_services_for_framework_slug:
        if remove_services_for_framework_slug not in frameworks_services:
            abort(400, 'No services for framework')
        if not any(i['status'] == 'published' for i in frameworks_services[remove_services_for_framework_slug]):
            abort(400, 'No published services on framework')

        remove_services_for_framework = next(filter(
            lambda i: i['slug'] == remove_services_for_framework_slug,
            frameworks
        ))
    else:
        remove_services_for_framework = None

    return render_template(
        'view_supplier_services.html',
        frameworks=frameworks,
        frameworks_services=frameworks_services,
        supplier=supplier,
        remove_services_for_framework=remove_services_for_framework,
    )


@main.route('/suppliers/<int:supplier_id>/services', methods=['POST'])
@role_required('admin-ccs-category')
def disable_supplier_services(supplier_id):
    remove_services_for_framework = request.args.get('remove')
    if not remove_services_for_framework:
        abort(400, 'Invalid framework')

    services = data_api_client.find_services(
        supplier_id=supplier_id,
        framework=remove_services_for_framework,
        status='published'
    )['services']
    if not services:
        abort(400, 'No published services on framework')

    for service in services:
        data_api_client.update_service_status(service['id'], 'disabled', current_user.email_address)

    flash("You removed all of {}'s '{}' services".format(services[0]['supplierName'], services[0]['frameworkName']))
    return redirect(url_for('.find_supplier_services', supplier_id=supplier_id))


@main.route('/suppliers/<int:supplier_id>/invite-user', methods=['POST'])
@role_required('admin')
def invite_user(supplier_id):
    invite_form = EmailAddressForm()

    try:
        suppliers = data_api_client.get_supplier(supplier_id)
        users = data_api_client.find_users(supplier_id)
    except HTTPError as e:
        current_app.logger.error(str(e), supplier_id)
        if e.status_code != 404:
            raise
        else:
            abort(404, "Supplier not found")

    if invite_form.validate_on_submit():
        send_user_account_email(
            'supplier',
            invite_form.email_address.data,
            current_app.config['NOTIFY_TEMPLATES']['invite_contributor'],
            extra_token_data={
                'supplier_id': supplier_id,
                'supplier_name': suppliers['suppliers']['name']
            },
            personalisation={
                'user': 'The Digital Marketplace team',
                'supplier': suppliers['suppliers']['name']
            }
        )

        data_api_client.create_audit_event(
            audit_type=AuditTypes.invite_user,
            user=current_user.email_address,
            object_type='suppliers',
            object_id=supplier_id,
            data={'invitedEmail': invite_form.email_address.data})

        flash('user_invited', 'success')
        return redirect(url_for('.find_supplier_users', supplier_id=supplier_id))
    else:
        return render_template(
            "view_supplier_users.html",
            invite_form=invite_form,
            move_user_form=MoveUserForm(),
            users=users["users"],
            supplier=suppliers["suppliers"]
        ), 400
