from datetime import datetime

from dmapiclient.audit import AuditTypes
from dmutils.formats import DATETIME_FORMAT
from flask import render_template, request

from .. import main
from ..auth import role_required
from ..helpers.sum_counts import format_snapshots
from ... import data_api_client


@main.route('/statistics/<string:framework_slug>', methods=['GET'])
@role_required('admin-ccs-sourcing', 'admin-framework-manager')
def view_statistics(framework_slug):

    snapshots = data_api_client.find_audit_events(
        audit_type=AuditTypes.snapshot_framework_stats,
        object_type='frameworks',
        object_id=framework_slug,
        per_page=1260
    )['auditEvents']
    framework = data_api_client.get_framework(framework_slug)['frameworks']
    if framework['status'] == 'open':
        snapshots.append(
            {
                'data': data_api_client.get_framework_stats(framework_slug),
                'createdAt': datetime.utcnow().strftime(DATETIME_FORMAT)
            }
        )

    return render_template(
        "view_statistics.html",
        framework=framework,
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
            lot['slug']: {
                'lot': lot['slug'],
                'status': 'submitted',
            } for lot in framework['lots']
        }),
        lots=framework['lots'],
        lot_table_headings=["Date and time"] + [lot['name'] for lot in framework['lots']],
        interested_suppliers=format_snapshots(snapshots, 'interested_suppliers', {
            'interested_only': {
                'declaration_status': [None, 'started'],
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
        })
    )
