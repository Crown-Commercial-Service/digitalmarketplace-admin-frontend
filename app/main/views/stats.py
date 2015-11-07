from datetime import datetime

from flask import render_template, abort, request
from flask_login import login_required, current_user, flash

from dmutils.apiclient import HTTPError
from dmutils.audit import AuditTypes
from dmutils.formats import DATETIME_FORMAT

from ..helpers.sum_counts import format_snapshots
from .. import main
from . import get_template_data
from ... import data_api_client
from ..auth import role_required


@main.route('/statistics/<string:framework_slug>', methods=['GET'])
@login_required
@role_required('admin', 'admin-ccs-category', 'admin-ccs-sourcing')
def view_statistics(framework_slug):

    try:
        snapshots = data_api_client.find_audit_events(
            audit_type=AuditTypes.snapshot_framework_stats,
            per_page=1260
        )['auditEvents']
        framework = data_api_client.get_framework(framework_slug)['frameworks']
        if framework['status'] is 'open':
            snapshots.append(
                {
                    'data': data_api_client.get_framework_stats(framework_slug),
                    'createdAt': datetime.utcnow().strftime(DATETIME_FORMAT)
                }
            )
    except HTTPError as error:
        abort(error.status_code)

    return render_template(
        "view_statistics.html",
        big_screen_mode=(request.args.get('big_screen_mode') == 'yes'),
        services_by_status=format_snapshots(snapshots, 'services', {
            'draft': {
                'status': 'not-submitted'
            },
            'complete': {
                'status': 'submitted',
                'declaration_made': False
            },
            'submitted': {
                'status': 'submitted',
                'declaration_made': True
            }
        }),
        services_by_lot=format_snapshots(snapshots, 'services', {
            'iaas': {'lot': ['IaaS', 'iaas']},
            'paas': {'lot': ['PaaS', 'paas']},
            'saas': {'lot': ['SaaS', 'saas']},
            'scs':  {'lot': ['SCS', 'scs']},
        }),
        interested_suppliers=format_snapshots(snapshots, 'interested_suppliers', {
            'interested_only': {
                'declaration_status': None,
                'has_completed_services': False
            },
            'declaration_only': {
                'declaration_status': 'complete',
                'has_completed_services': False
            },
            'completed_services_only': {
                'declaration_status': [None, 'started'],
                'has_completed_services': True
            },
            'valid_submission': {
                'declaration_status': 'complete',
                'has_completed_services': True
            }
        }),
        users=format_snapshots(snapshots, 'supplier_users', {
            'never_logged_in': {
                'recent_login': None
            },
            'not_logged_in_recently': {
                'recent_login': False
            },
            'logged_in_recently': {
                'recent_login': True
            }
        }),
        **get_template_data()
    )
