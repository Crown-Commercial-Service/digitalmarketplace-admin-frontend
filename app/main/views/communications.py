from pathlib import PurePath

from dmutils import s3  # this style of import so we only have to mock once
from dmutils.documents import file_is_pdf, file_is_csv, file_is_open_document_format, get_signed_url
from dmutils.flask import timed_render_template as render_template
from flask import redirect, url_for, current_app, request, flash, abort

from .. import main
from ..auth import role_required
from ... import data_api_client
from ..helpers.frameworks import get_framework_or_404


def _get_comm_type_root(framework_slug, comm_type):
    # PurePath has the advantage that it doesn't handle ".." elements specially, and so we're safe from a whole
    # category of tricks
    return PurePath(framework_slug) / "communications" / "updates" / f"{comm_type}s"


_comm_types = ("communication", "clarification",)


@main.route('/communications/<framework_slug>', methods=['GET'])
@role_required('admin-framework-manager')
def manage_communications(framework_slug):
    communications_bucket = s3.S3(current_app.config['DM_COMMUNICATIONS_BUCKET'])
    framework = data_api_client.get_framework(framework_slug)['frameworks']

    # Get the last items from the timestamp-ordered buckets, in order to show the most recently updated timestamps
    # The "or [None]" ensures we have a list with at least one item (None) when no files exist in the bucket
    communications = communications_bucket.list(
        '{}/communications/updates/communications'.format(framework_slug), load_timestamps=True
    ) or [None]
    clarifications = communications_bucket.list(
        '{}/communications/updates/clarifications'.format(framework_slug), load_timestamps=True
    ) or [None]

    return render_template(
        'manage_communications.html',
        # Pass in the last (most recent) clarification and communication from the lists; used to show "last modified"
        clarification=clarifications[-1],
        communication=communications[-1],
        framework=framework
    )


@main.route('/communications/<framework_slug>/files/<string:comm_type>/<path:filepath>', methods=['GET'])
@role_required('admin-framework-manager')
def download_communication(framework_slug, comm_type, filepath):
    if comm_type not in _comm_types:
        abort(404)

    # ensure this is a real framework
    get_framework_or_404(data_api_client, framework_slug)

    bucket = s3.S3(current_app.config['DM_COMMUNICATIONS_BUCKET'])
    full_path = _get_comm_type_root(framework_slug, comm_type) / filepath
    url = get_signed_url(bucket, str(full_path), current_app.config["DM_ASSETS_URL"])
    if not url:
        abort(404)

    return redirect(url)


@main.route('/communications/<framework_slug>', methods=['POST'])
@role_required('admin-framework-manager')
def upload_communication(framework_slug):
    communications_bucket = s3.S3(current_app.config['DM_COMMUNICATIONS_BUCKET'])
    errors = {}

    if request.files.get('communication'):
        the_file = request.files['communication']
        if not (file_is_open_document_format(the_file) or file_is_csv(the_file)):
            errors['communication'] = 'not_open_document_format_or_csv'
            flash('Communication file is not an open document format or a CSV.', 'error')

        if 'communication' not in errors.keys():
            path = "{}/communications/updates/communications/{}".format(framework_slug, the_file.filename)
            communications_bucket.save(
                path, the_file, acl='bucket-owner-full-control', download_filename=the_file.filename
            )
            flash('New communication was uploaded.')

    if request.files.get('clarification'):
        the_file = request.files['clarification']
        if not file_is_pdf(the_file):
            errors['clarification'] = 'not_pdf'
            flash('Clarification file is not a PDF.', 'error')

        if 'clarification' not in errors.keys():
            path = "{}/communications/updates/clarifications/{}".format(framework_slug, the_file.filename)
            communications_bucket.save(
                path, the_file, acl='bucket-owner-full-control', download_filename=the_file.filename
            )
            flash('New clarification was uploaded.')

    return redirect(url_for('.manage_communications', framework_slug=framework_slug))


@main.route('/communications/<framework_slug>/delete/<string:comm_type>/<path:filepath>', methods=("GET", "POST",))
@role_required('admin-framework-manager')
def delete_communication(framework_slug, comm_type, filepath):
    if comm_type not in _comm_types:
        abort(404)

    framework = get_framework_or_404(data_api_client, framework_slug)

    if request.method == "POST":
        if "confirm" not in request.form:
            abort(400, "Expected 'confirm' parameter in POST request")

        communications_bucket = s3.S3(current_app.config['DM_COMMUNICATIONS_BUCKET'])
        full_path = _get_comm_type_root(framework_slug, comm_type) / filepath

        # do this check ourselves - deleting an object in S3 silently has no effect, forwarding this behaviour to the
        # user is a confusing thing to do
        if not communications_bucket.path_exists(str(full_path)):
            abort(404, f"{filepath} not present in S3 bucket")

        communications_bucket.delete_key(str(full_path))

        flash(f"{comm_type.capitalize()} ‘{filepath}’ was deleted for {framework['name']}.")
        return redirect(url_for('.manage_communications', framework_slug=framework_slug))

    return render_template(
        'confirm_communications_deletion.html',
        framework=framework,
        comm_type=comm_type,
        filepath=filepath,
    )
