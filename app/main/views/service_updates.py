from datetime import datetime, timedelta

from flask import request, render_template, redirect, url_for, abort
from flask_login import login_required, current_user

from dmapiclient.audit import AuditTypes

from ... import data_api_client
from .. import main
from ..auth import role_required


@main.route('/service-status-updates', methods=['GET'])
@main.route('/service-status-updates/<day>', methods=['GET'])
@main.route('/service-status-updates/<day>/page-<int:page>', methods=['GET'])
@login_required
@role_required('admin', 'admin-ccs-category')
def service_status_update_audits(day=None, page=1):

    if day is None:
        return redirect(url_for(
            '.service_status_update_audits',
            day=datetime.today().strftime('%Y-%m-%d')
        ))

    try:
        day_as_datetime = datetime.strptime(day, '%Y-%m-%d')
    except ValueError:
        abort(404)

    status_update_audit_events = data_api_client.find_audit_events(
        audit_type=AuditTypes.update_service_status,
        audit_date=day,
        page=page,
        latest_first=True
    )

    return render_template(
        "service_status_update_audits.html",
        audit_events=status_update_audit_events['auditEvents'],
        day=day,
        day_as_datetime=day_as_datetime,
        previous_day=day_as_datetime - timedelta(1),
        next_day=day_as_datetime + timedelta(1) if day_as_datetime + timedelta(1) < datetime.today() else None,
        previous_page=status_update_audit_events.get('links', {}).get('prev'),
        next_page=status_update_audit_events.get('links', {}).get('next'),
        page=page
    )


@main.route('/services/updates/unacknowledged', methods=['GET'])
@login_required
@role_required('admin', 'admin-ccs-category')
def service_update_audits():
    audit_events_response = data_api_client.find_audit_events(
        audit_type=AuditTypes.update_service,
        acknowledged='false',
        latest_first='false',
        earliest_for_each_object='true',
    )

    return render_template(
        "service_update_audits.html",
        audit_events=audit_events_response['auditEvents'],
        has_next=bool(audit_events_response['links'].get('next')),
    )


@main.route('/services/updates/acknowledged', methods=['GET'])
@login_required
@role_required('admin', 'admin-ccs-category')
def acknowledged_services():
    audit_events_response = data_api_client.find_audit_events(
        audit_type=AuditTypes.update_service,
        acknowledged='true',
        latest_first='false',
        earliest_for_each_object='true',
    )

    return render_template(
        "acknowledged_services.html",
        audit_events=audit_events_response['auditEvents'],
    )


@main.route('/services/<service_id>/updates/<int:audit_id>/acknowledge', methods=['POST'])
@login_required
@role_required('admin-ccs-category')
def submit_service_update_acknowledgment(service_id, audit_id):
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

    return redirect(url_for('.service_update_audits'))
