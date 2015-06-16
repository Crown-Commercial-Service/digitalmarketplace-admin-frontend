import time
from datetime import datetime
from flask import render_template, request
from . import main
from .helpers.auth import is_authenticated


@main.route('/activity', methods=['GET'])
def activity():
    return render_template(
        "activity.html",
        today=datetime.now().strftime("%d/%m/%Y"),
        audit_events=None,
        **get_template_data())


@main.route('/activity', methods=['POST'])
def submit_activity():
    print "\n\n\n\n\n request.form['acknowledged']  \n\n\n"
    print request.form['acknowledged']
    print request.form['activity-date']
    print validate_date(request.form['activity-date'])
    print "\n\n\n\n\n "
    return render_template(
        "activity.html",
        today=datetime.now().strftime("%d/%m/%Y"),
        audit_events=None,
        **get_template_data())


def validate_date(date):
    if date:
        try:
            actual_date = datetime.strptime(date, "%d/%m/%Y")
            return actual_date.strftime('%Y-%m-%d')
        except ValueError:
            return None
    return None


def get_template_data(merged_with={}):
    template_data = dict(main.config['BASE_TEMPLATE_DATA'], **merged_with)
    template_data["authenticated"] = is_authenticated()
    return template_data
