from flask import render_template, abort, request
from flask_login import login_required, current_user, flash

from dmutils.apiclient import HTTPError

from ..helpers.sum_counts import label_and_count
from .. import main
from . import get_template_data
from ... import data_api_client


@main.route('/statistics/<string:framework_slug>', methods=['GET'])
@login_required
def view_statistics(framework_slug):

    try:
        stats = data_api_client.get_framework_stats(framework_slug)
    except HTTPError as error:
        abort(error.status_code)

    return render_template(
        "view_statistics.html",
        big_screen_mode=(request.args.get('big_screen_mode') == 'yes'),
        services_by_status=label_and_count(stats['services'], {
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
        services_by_lot=label_and_count(stats['services'], {
            'IaaS': {'lot': 'IaaS'},
            'PaaS': {'lot': 'PaaS'},
            'SaaS': {'lot': 'SaaS'},
            'SCS':  {'lot': 'SCS'},
        }),
        interested_suppliers=label_and_count(stats['interested_suppliers'], {
            'interested_only': {
                'has_made_declaration': False,
                'has_completed_services': False
            },
            'declaration_only': {
                'has_made_declaration': True,
                'has_completed_services': False
            },
            'completed_services_only': {
                'has_made_declaration': False,
                'has_completed_services': True
            },
            'valid_submission': {
                'has_made_declaration': True,
                'has_completed_services': True
            }
        }),
        users=label_and_count(stats['supplier_users'], {
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
        stats=stats,
        **get_template_data()
    )
