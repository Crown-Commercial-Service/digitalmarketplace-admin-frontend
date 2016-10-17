from collections import OrderedDict

from dmutils.documents import degenerate_document_path_and_return_doc_name
from flask import render_template, redirect, url_for, abort, request
from flask_login import login_required
from dateutil.parser import parse as parse_date
from six import next

from dmutils.formats import datetimeformat

from .. import main
from ..auth import role_required
from ... import data_api_client


_status_labels = OrderedDict((
    ("signed", "Waiting for countersigning"),
    ("on-hold", "On hold"),
    ("approved,countersigned", "Countersigned"),  # ugly, but i don't want to start inventing new status values - much
                                                  # easier to just act as a filter
))


def _get_ordered_supplier_frameworks(framework_slug, status=None):
    supplier_frameworks = data_api_client.find_framework_suppliers(
        framework_slug,
        agreement_returned=True,
        **({"statuses": status} if status else {})
    )['supplierFrameworks']

    # API now returns SupplierFrameworks by agreementReturnedAt ascending (oldest first)
    return supplier_frameworks


@main.route('/agreements/<framework_slug>', methods=['GET'])
@login_required
@role_required('admin', 'admin-ccs-sourcing')
def list_agreements(framework_slug):
    framework = data_api_client.get_framework(framework_slug)['frameworks']

    status = request.args.get("status")
    if status and status not in _status_labels:
        abort(400)

    supplier_frameworks = _get_ordered_supplier_frameworks(framework_slug, status=status)

    for supplier_framework in supplier_frameworks:
        supplier_framework['agreementReturnedAt'] = datetimeformat(
            parse_date(supplier_framework['agreementReturnedAt']))

    return render_template(
        "view_agreements_g8.html" if framework_slug == "g-cloud-8" else 'view_agreements.html',
        framework=framework,
        supplier_frameworks=supplier_frameworks,
        degenerate_document_path_and_return_doc_name=lambda x: degenerate_document_path_and_return_doc_name(x),
        status=status,
        status_labels=_status_labels,
    )


@main.route('/suppliers/<int:supplier_id>/agreements/<framework_slug>/next', methods=('GET',))
@login_required
@role_required('admin', 'admin-ccs-sourcing')
def next_agreement(supplier_id, framework_slug):
    supplier_frameworks = _get_ordered_supplier_frameworks(framework_slug)
    supplier_frameworks_iter = iter(supplier_frameworks)

    try:
        while next(supplier_frameworks_iter).get("supplierId") != supplier_id:
            pass
    except StopIteration:
        # reached the end of supplier_frameworks_iter without finding an entry for supplier_id. supplier possibly
        # doesn't exist or doesn't have a signed agreement yet
        abort(404)

    try:
        next_supplier_framework = next(supplier_frameworks_iter)
    except StopIteration:
        # this was the last one.
        return redirect(url_for(
            '.list_agreements',
            framework_slug=framework_slug,
        ))

    return redirect(url_for(
        '.view_signed_agreement',
        supplier_id=next_supplier_framework["supplierId"],
        framework_slug=next_supplier_framework["frameworkSlug"],
    ))
