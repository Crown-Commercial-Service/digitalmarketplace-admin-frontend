from datetime import datetime, timedelta
from itertools import groupby, islice

from flask import request, render_template, redirect, url_for, abort
from flask_login import login_required, current_user
from six import next

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


@main.route('/services/updates', methods=['GET'])
@login_required
@role_required('admin', 'admin-ccs-category')
def acknowledged_services():
    audit_events = data_api_client.find_audit_events(
        audit_type=AuditTypes.update_service,
        acknowledged='true',
        latest_first='false',
        earliest_for_each_object='true',
    )

    return render_template(
        "acknowledged_services.html",
        audit_events=audit_events['auditEvents'],
    )


@main.route('/service-updates/<audit_id>/acknowledge', methods=['POST'])
@login_required
@role_required('admin')
def submit_service_update_acknowledgment(audit_id):
    form = ServiceUpdateAuditEventsForm(request.form)
    if form.validate():
        data_api_client.acknowledge_audit_event(
            audit_id, current_user.email_address)
        return redirect(
            url_for(
                '.service_update_audits',
                audit_date=form.audit_date.data,
                acknowledged=form.acknowledged.data)
        )
    else:
        return render_template(
            "service_update_audits.html",
            today=datetime.utcnow().strftime(DATETIME_FORMAT),
            audit_events=None,
            acknowledged=form.default_acknowledged(),
            form=form
        ), 400
