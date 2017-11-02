from flask import render_template, redirect, url_for, current_app, \
    request, flash

from .. import main
from ..auth import role_required
from ... import data_api_client

from dmutils import s3  # this style of import so we only have to mock once
from dmutils.documents import file_is_pdf, file_is_csv, file_is_open_document_format


@main.route('/communications/<framework_slug>', methods=['GET'])
@role_required('admin', 'admin-ccs-category')
def manage_communications(framework_slug):
    communications_bucket = s3.S3(current_app.config['DM_COMMUNICATIONS_BUCKET'])
    framework = data_api_client.get_framework(framework_slug)['frameworks']

    clarification = next(iter(communications_bucket.list(
        '{}/communications/updates/clarifications'.format(framework_slug), load_timestamps=True
    )), None)
    communication = next(iter(communications_bucket.list(
        '{}/communications/updates/communications'.format(framework_slug), load_timestamps=True
    )), None)

    return render_template(
        'manage_communications.html',
        clarification=clarification,
        communication=communication,
        framework=framework
    )


@main.route('/communications/<framework_slug>', methods=['POST'])
@role_required('admin', 'admin-ccs-category')
def upload_communication(framework_slug):
    communications_bucket = s3.S3(current_app.config['DM_COMMUNICATIONS_BUCKET'])
    errors = {}

    if request.files.get('communication'):
        the_file = request.files['communication']
        if not (file_is_open_document_format(the_file) or file_is_csv(the_file)):
            errors['communication'] = 'not_open_document_format_or_csv'

        if 'communication' not in errors.keys():
            path = "{}/communications/updates/communications/{}".format(framework_slug, the_file.filename)
            communications_bucket.save(path, the_file, acl='private', download_filename=the_file.filename)
            flash('communication', 'upload_communication')

    if request.files.get('clarification'):
        the_file = request.files['clarification']
        if not file_is_pdf(the_file):
            errors['clarification'] = 'not_pdf'

        if 'clarification' not in errors.keys():
            path = "{}/communications/updates/clarifications/{}".format(framework_slug, the_file.filename)
            communications_bucket.save(path, the_file, acl='private', download_filename=the_file.filename)
            flash('clarification', 'upload_communication')

    if len(errors) > 0:
        for category, message in errors.items():
            flash(category, message)
    return redirect(url_for('.manage_communications', framework_slug=framework_slug))
