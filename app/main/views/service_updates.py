from datetime import datetime

from flask import request, render_template, redirect, url_for, session

from dmutils.audit import AuditTypes

from ... import data_api_client
from .. import main
from ..forms import ServiceUpdateAuditEventsForm
from . import get_template_data


@main.route('/service-updates', methods=['GET'])
def service_update_audits():
    form = ServiceUpdateAuditEventsForm(request.args, csrf_enabled=False)

    if form.validate():
        audit_events = data_api_client.find_audit_events(
            audit_type=AuditTypes.update_service.value,
            acknowledged=form.default_acknowledged(),
            audit_date=form.format_date()
        )

        return render_template(
            "service_update_audits.html",
            today=form.format_date_for_display(),
            acknowledged=form.default_acknowledged(),
            audit_events=audit_events['auditEvents'],
            form=form,
            **get_template_data())
    else:
        return render_template(
            "service_update_audits.html",
            today=datetime.now(),
            acknowledged=form.default_acknowledged(),
            audit_events=[],
            form=form,
            **get_template_data()), 400


@main.route('/service-updates/<audit_id>/acknowledge', methods=['POST'])
def submit_service_update_acknowledgment(audit_id):
    form = ServiceUpdateAuditEventsForm(request.form)
    if form.validate():
        data_api_client.acknowledge_audit_event(audit_id, session['username'])
        return redirect(
            url_for(
                '.service_update_audits',
                audit_date=form.audit_date.data,
                acknowledged=form.acknowledged.data)
        )
    else:
        return render_template(
            "service_update_audits.html",
            today=datetime.now(),
            audit_events=None,
            acknowledged=form.default_acknowledged(),
            form=form,
            **get_template_data()), 400
