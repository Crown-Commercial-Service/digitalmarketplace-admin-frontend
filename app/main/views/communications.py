from flask import render_template, redirect, url_for, current_app, \
    request, flash
from flask_login import login_required

from .. import main
from ..auth import role_required
from ... import data_api_client
from . import get_template_data

from dmutils import s3
from dmutils.documents import file_is_pdf, file_is_zip


def _get_path(framework_slug, path):
    return '{}/communications/{}'.format(framework_slug, path)


def _get_itt_pack_path(framework_slug):
    return '{0}/communications/{0}-itt-pack.zip'.format(framework_slug)


@main.route('/communications/<framework_slug>', methods=['GET'])
@login_required
@role_required('admin')
def manage_communications(framework_slug):
    communications_bucket = s3.S3(current_app.config['DM_COMMUNICATIONS_BUCKET'])
    framework = data_api_client.get_framework(framework_slug)['frameworks']

    itt_pack = next(iter(communications_bucket.list(_get_itt_pack_path(framework_slug))), None)
    clarification = next(iter(communications_bucket.list(_get_path(framework_slug, 'updates/clarifications'))), None)
    communication = next(iter(communications_bucket.list(_get_path(framework_slug, 'updates/communications'))), None)

    return render_template(
        'manage_communications.html',
        itt_pack=itt_pack,
        clarification=clarification,
        communication=communication,
        framework=framework,
        **get_template_data()
    )


@main.route('/communications/<framework_slug>', methods=['POST'])
@login_required
@role_required('admin')
def upload_communication(framework_slug):
    communications_bucket = s3.S3(current_app.config['DM_COMMUNICATIONS_BUCKET'])
    errors = {}

    if request.files.get('communication'):
        the_file = request.files['communication']
        if not file_is_pdf(the_file):
            errors['communication'] = 'not_pdf'

        if 'communication' not in errors.keys():
            filename = _get_path(framework_slug, 'updates/communications') + '/' + the_file.filename
            communications_bucket.save(filename, the_file)
            flash('communication', 'upload_communication')

    if request.files.get('clarification'):
        the_file = request.files['clarification']
        if not file_is_pdf(the_file):
            errors['clarification'] = 'not_pdf'

        if 'clarification' not in errors.keys():
            filename = _get_path(framework_slug, 'updates/clarifications') + '/' + the_file.filename
            communications_bucket.save(filename, the_file)
            flash('clarification', 'upload_communication')

    if request.files.get('itt_pack'):
        the_file = request.files['itt_pack']
        if not file_is_zip(the_file):
            errors['itt_pack'] = 'not_zip'

        if 'itt_pack' not in errors.keys():
            filename = _get_itt_pack_path(framework_slug)
            communications_bucket.save(filename, the_file)
            flash('itt_pack', 'upload_communication')

    if len(errors) > 0:
        print errors
        for category, message in errors.items():
            flash(category, message)
    return redirect(url_for('.manage_communications', framework_slug=framework_slug))
