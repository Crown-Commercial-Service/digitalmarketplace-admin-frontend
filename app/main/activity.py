from datetime import datetime
from flask import render_template, redirect, url_for, request
from . import main
from .. import data_api_client
from .helpers.auth import is_authenticated
from forms import FilterAuditEventsForm
from dmutils.audit import AuditTypes


@main.route('/audits', methods=['GET'])
def audits():
    form = FilterAuditEventsForm(request.args, csrf_enabled=False)

    if form.validate():
        audit_events = data_api_client.find_audit_events(
            audit_type=AuditTypes.update_service.value,
            acknowledged=form.default_acknowledged(),
            audit_date=form.format_date()
        )
        if not form.acknowledged.data:
            form.acknowledged.data = 'all'
        return render_template(
            "activity.html",
            today=form.format_date_for_display(),
            acknowledged=form.default_acknowledged(),
            audit_events=audit_events['auditEvents'],
            form=form,
            **get_template_data())
    else:
        return render_template(
            "activity.html",
            today=datetime.now().strftime("%d/%m/%Y"),
            acknowledged=form.default_acknowledged(),
            audit_events=[],
            form=form,
            **get_template_data()), 400


@main.route('/acknowledge/<audit_id>', methods=['POST'])
def submit_acknowledgment(audit_id):
    form = FilterAuditEventsForm()
    if form.validate():
        return redirect(
            url_for(
                '.audits',
                audit_date=form.audit_date.data,
                acknowledged=form.acknowledged.data)
        )
    else:
        return render_template(
            "activity.html",
            today=datetime.now().strftime("%d/%m/%Y"),
            audit_events=None,
            form=form,
            **get_template_data())


def get_template_data(merged_with={}):
    template_data = dict(main.config['BASE_TEMPLATE_DATA'], **merged_with)
    template_data["authenticated"] = is_authenticated()
    return template_data
