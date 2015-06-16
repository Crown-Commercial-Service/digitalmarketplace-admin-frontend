from datetime import datetime
from flask import render_template, redirect, url_for, request
from . import main
from .helpers.auth import is_authenticated
from forms import FilterAuditEventsForm


@main.route('/audits', methods=['GET'])
def audits():
    form = FilterAuditEventsForm(request.args, csrf_enabled=False)

    if form.validate():
        return render_template(
            "activity.html",
            today=datetime.now().strftime("%d/%m/%Y"),
            audit_events=None,
            form=form,
            **get_template_data())
    else:
        return render_template(
            "activity.html",
            today=datetime.now().strftime("%d/%m/%Y"),
            audit_events=None,
            form=form,
            **get_template_data())


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
