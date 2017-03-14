from flask import render_template, redirect, url_for, current_app, \
    request, flash
from flask_login import login_required

from .. import main
from ..auth import role_required
from ... import data_api_client

from dmutils import s3
from dmutils.documents import file_is_pdf, file_is_csv, file_is_open_document_format


def _get_path(framework_slug, path):
    return '{}/communications/{}'.format(framework_slug, path)


def _save_file(bucket, framework_slug, path, the_file, flash_message):
    path = "{}/{}".format(_get_path(framework_slug, path), the_file.filename)
    download_filename = "{}-{}".format(framework_slug, the_file.filename)
    bucket.save(path, the_file, download_filename=download_filename)
    flash(flash_message, 'upload_communication')


@main.route('/communications/<framework_slug>', methods=['GET'])
@login_required
@role_required('admin')
def manage_communications(framework_slug):
    communications_bucket = s3.S3(current_app.config['DM_COMMUNICATIONS_BUCKET'])
    framework = data_api_client.get_framework(framework_slug)['frameworks']

    clarification = next(iter(communications_bucket.list(_get_path(framework_slug, 'updates/clarifications'))), None)
    communication = next(iter(communications_bucket.list(_get_path(framework_slug, 'updates/communications'))), None)

    return render_template(
        'manage_communications.html',
        clarification=clarification,
        communication=communication,
        framework=framework
    )


@main.route('/communications/<framework_slug>', methods=['POST'])
@login_required
@role_required('admin')
def upload_communication(framework_slug):
    communications_bucket = s3.S3(current_app.config['DM_COMMUNICATIONS_BUCKET'])
    errors = {}

    if request.files.get('communication'):
        the_file = request.files['communication']
        if not (file_is_open_document_format(the_file) or file_is_csv(the_file)):
            errors['communication'] = 'not_open_document_format_or_csv'

        if 'communication' not in errors.keys():
            _save_file(communications_bucket, framework_slug, 'updates/communications', the_file, 'communication')

    if request.files.get('clarification'):
        the_file = request.files['clarification']
        if not file_is_pdf(the_file):
            errors['clarification'] = 'not_pdf'

        if 'clarification' not in errors.keys():
            _save_file(communications_bucket, framework_slug, 'updates/clarifications', the_file, 'clarification')

    if len(errors) > 0:
        for category, message in errors.items():
            flash(category, message)
    return redirect(url_for('.manage_communications', framework_slug=framework_slug))
