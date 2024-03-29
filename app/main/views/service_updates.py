from dmapiclient.audit import AuditTypes
from dmutils import s3
from dmutils.documents import get_signed_url
from dmutils.flask import timed_render_template as render_template
from flask import abort, flash, redirect, url_for, current_app
from flask_login import current_user

from .. import main
from ..auth import role_required
from ... import data_api_client


APPROVED_SERVICE_EDITS_MESSAGE = "The changes to service {service_id} were approved."


@main.route('/services/updates/unapproved', methods=['GET'])
@role_required('admin-ccs-category')
def service_update_audits():
    audit_events_response = data_api_client.find_audit_events(
        audit_type=AuditTypes.update_service,
        acknowledged='false',
        latest_first='false',
        earliest_for_each_object='true',
    )

    return render_template(
        "service_updates_unapproved.html",
        audit_events=audit_events_response['auditEvents'],
        has_next=bool(audit_events_response['links'].get('next')),
    )


@main.route('/services/<service_id>/updates/<int:audit_id>/approve', methods=['POST'])
@role_required('admin-ccs-category')
def submit_service_update_approval(service_id, audit_id):
    audit_event = data_api_client.get_audit_event(audit_id)["auditEvents"]

    if audit_event["data"]["serviceId"] != service_id or audit_event["type"] != "update_service":
        abort(404)

    if audit_event['acknowledged']:
        abort(410)

    data_api_client.acknowledge_service_update_including_previous(
        service_id,
        audit_event["id"],
        current_user.email_address
    )
    flash(APPROVED_SERVICE_EDITS_MESSAGE.format(service_id=service_id))
    return redirect(url_for('.service_update_audits'))


@main.route('/services/updates/approved/<date>', methods=['GET'])
@role_required('admin-ccs-category')
def download_approved_service_edits(date):
    reports_bucket = s3.S3(
        current_app.config['DM_REPORTS_BUCKET'], endpoint_url=current_app.config.get("DM_S3_ENDPOINT_URL")
    )

    path = f"common/reports/approved-service-edits-{date}.csv"
    url = get_signed_url(reports_bucket, path, current_app.config['DM_ASSETS_URL']) or abort(404)
    return redirect(url)
