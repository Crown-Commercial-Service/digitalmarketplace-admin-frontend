from datetime import datetime, timedelta

from flask import request, render_template, redirect, url_for, abort
from flask_login import login_required, current_user

from dmapiclient.audit import AuditTypes
from dmutils.formats import DATETIME_FORMAT

from ... import data_api_client
from .. import main
from ..auth import role_required
from ..forms import ServiceUpdateAuditEventsForm


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
    except ValueError as err:
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


@main.route('/service-updates', methods=['GET'])
@login_required
@role_required('admin', 'admin-ccs-category')
def service_update_audits():
    form = ServiceUpdateAuditEventsForm(request.args, csrf_enabled=False)

    if not form.validate():
        return render_template(
            "service_update_audits.html",
            today=datetime.utcnow().strftime(DATETIME_FORMAT),
            acknowledged=form.default_acknowledged(),
            audit_events=[],
            form=form
        ), 400

    audit_events = data_api_client.find_audit_events(
        audit_type=AuditTypes.update_service,
        acknowledged=form.default_acknowledged(),
        audit_date=form.format_date(),
        page=form.page.data
    )

    return render_template(
        "service_update_audits.html",
        today=form.format_date_for_display().strftime(DATETIME_FORMAT),
        acknowledged=form.default_acknowledged(),
        audit_events=audit_events['auditEvents'],
        current_page=form.page.data,
        prev_page_exists=bool(audit_events['links'].get('prev')),
        next_page_exists=bool(audit_events['links'].get('next')),
        form=form
    )


@main.route('/services/<service_id>/updates/<int:audit_id>/acknowledge', methods=['POST'])
@login_required
@role_required('admin')
def submit_service_update_acknowledgment(service_id, audit_id):
    audit_event = data_api_client.get_audit_event(audit_id)["auditEvents"]

    if audit_event["data"]["serviceId"] != service_id or audit_event["type"] != "update_service":
        abort(404)

    if audit_event['acknowledged']:
        abort(410)

    data_api_client.acknowledge_audit_event(
        audit_event["id"],
        current_user.email_address,
        include_previous_for_object=True,
    )

    return redirect(url_for('.service_update_audits'))
