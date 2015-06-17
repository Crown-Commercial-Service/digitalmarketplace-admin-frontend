from datetime import datetime
from flask import render_template, redirect, url_for, request, session
from . import main
from .. import data_api_client
from .helpers.auth import is_authenticated
from forms import ServiceUpdateAuditEventsForm
from dmutils.audit import AuditTypes


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
            today=datetime.now().strftime("%d/%m/%Y"),
            acknowledged=form.default_acknowledged(),
            audit_events=[],
            form=form,
            **get_template_data()), 400


@main.route('/service-updates/<audit_id>/acknowledge', methods=['POST'])
def submit_service_update_acknowledgment(audit_id):
    form = ServiceUpdateAuditEventsForm(request.args)
    print form.audit_date.data
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
            today=datetime.now().strftime("%d/%m/%Y"),
            audit_events=None,
            acknowledged=form.default_acknowledged(),
            form=form,
            **get_template_data()), 400


def get_template_data(merged_with={}):
    template_data = dict(main.config['BASE_TEMPLATE_DATA'], **merged_with)
    template_data["authenticated"] = is_authenticated()
    return template_data
