from flask import current_app, flash, render_template, request, redirect, \
    session, url_for
from dmutils.apiclient import HTTPError

from .. import data_api_client
from . import main
from dmutils.validation import Validate
from dmutils.content_loader import ContentLoader
from dmutils.presenters import Presenters
from dmutils.s3 import S3
from .helpers.auth import check_auth, is_authenticated




@main.route('/activity', methods=['GET'])
def activity():
    audits = data_api_client.find_audit_events()
    return render_template("activity.html", audit_events=audits['auditEvents'], **get_template_data())

def get_template_data(merged_with={}):
    template_data = dict(main.config['BASE_TEMPLATE_DATA'], **merged_with)
    template_data["authenticated"] = is_authenticated()
    return template_data
