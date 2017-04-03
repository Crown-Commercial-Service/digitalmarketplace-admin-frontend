from datetime import datetime

from flask import render_template, request
from flask_login import login_required

from dmapiclient.audit import AuditTypes
from dmutils.formats import DATETIME_FORMAT

from ..helpers.sum_counts import format_snapshots, format_metrics
from .. import main
from ... import data_api_client
from ..auth import role_required


@main.route('/statistics/applications', methods=['GET'])
@login_required
@role_required('admin', 'admin-ccs-category', 'admin-ccs-sourcing')
def view_application_statistics():
    raw_applications = data_api_client.req.metrics().applications().history().get()
    applications = format_metrics(raw_applications)
    domains = data_api_client.req.metrics().domains().get()
    seller_types = data_api_client.req.metrics().applications().seller_types().get()
    steps = data_api_client.req.metrics().applications().steps().get()

    return render_template(
        "view_statistics.html",
        big_screen_mode=(request.args.get('big_screen_mode') == 'yes'),
        applications_by_status=applications,
        domains_by_status=applications,
        domains=domains,
        seller_types=seller_types,
        steps=steps
    )
