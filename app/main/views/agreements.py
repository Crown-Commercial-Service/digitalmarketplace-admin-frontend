from collections import OrderedDict

from dateutil.parser import parse as parse_date
from dmutils.documents import degenerate_document_path_and_return_doc_name
from dmutils.flask import timed_render_template as render_template
from dmutils.formats import datetimeformat
from flask import redirect, url_for, abort, request

from .. import main
from ..auth import role_required
from ... import data_api_client


def get_status_labels():
    return OrderedDict((
        ("signed", "Waiting for countersigning"),
        ("on-hold", "On hold"),
        ("approved,countersigned", "Countersigned"),  # ugly key, but i don't want to start inventing new status values
                                                      # much easier to just act as a filter
    ))


def _get_supplier_frameworks(framework_slug, status=None):
    return [
        supplier_framework for supplier_framework in data_api_client.find_framework_suppliers(
            framework_slug, agreement_returned=True,
            with_declarations=False,
            **({"statuses": status} if status else {})
        )['supplierFrameworks']
        if supplier_framework['onFramework']
    ]


@main.route('/agreements/<framework_slug>', methods=['GET'])
@role_required('admin-ccs-category', 'admin-ccs-sourcing', 'admin-framework-manager', 'admin-ccs-data-controller')
def list_agreements(framework_slug):
    framework = data_api_client.get_framework(framework_slug)['frameworks']
    status_labels = get_status_labels()

    status = request.args.get("status")
    if status and status not in status_labels:
        abort(400)

    supplier_frameworks = _get_supplier_frameworks(framework_slug, status=status)

    for supplier_framework in supplier_frameworks:
        supplier_framework['agreementReturnedAt'] = datetimeformat(
            parse_date(supplier_framework['agreementReturnedAt']))

    # Determine which template to use.
    # G-Cloud 7 and earlier frameworks do not have a frameworkAgreementVersion and use an old countersigning flow
    # G-Cloud 12 and newer frameworks use e-signature flow (countersignatures are automated)
    is_e_signature_flow = framework['isESignatureSupported']
    if framework.get('frameworkAgreementVersion'):
        template = "view_agreements_list.html"
        if is_e_signature_flow:
            status_labels['signed'] = "Waiting for automated countersigning"
    else:
        template = 'view_agreements.html'

    return render_template(
        template,
        framework=framework,
        supplier_frameworks=supplier_frameworks,
        degenerate_document_path_and_return_doc_name=lambda x: degenerate_document_path_and_return_doc_name(x),
        status=status,
        status_labels=status_labels,
        is_e_signature_flow=is_e_signature_flow
    )


@main.route('/suppliers/<int:supplier_id>/agreements/<framework_slug>/next', methods=('GET',))
@role_required('admin-ccs-category', 'admin-ccs-sourcing', 'admin-framework-manager', 'admin-ccs-data-controller')
def next_agreement(supplier_id, framework_slug):
    status = request.args.get("status")
    status_labels = get_status_labels()
    if status and status not in status_labels:
        abort(400)

    # note we are NOT requesting the status-filtered supplier_framework list - we can't be sure our requested supplier
    # will *be* in the filtered set (though it may have been at the time the url was generated) so for this view at
    # least, any status "filtering" we do must be here in python.
    supplier_frameworks = _get_supplier_frameworks(framework_slug)
    supplier_frameworks_iter = iter(supplier_frameworks)

    # first advance supplier_frameworks_iter to the requested supplier in the list, disregarding any status filter
    try:
        next(sf for sf in supplier_frameworks_iter if sf.get("supplierId") == supplier_id)
    except StopIteration:
        # reached the end of supplier_frameworks_iter without finding an entry for supplier_id. supplier possibly
        # doesn't exist or doesn't have a signed agreement yet
        abort(404)

    # now find whatever the "next" one (which satisfies any status requirement we have) is, remembering that a
    # status_labels key might be a comma-separated list of actual API statuses
    try:
        next_supplier_framework = next(
            sf for sf in supplier_frameworks_iter if (not status) or sf.get("agreementStatus") in status.split(",")
        )
    except StopIteration:
        # this was the last one.
        return redirect(url_for(
            '.list_agreements',
            framework_slug=framework_slug,
            status=status,
        ))

    return redirect(url_for(
        '.view_signed_agreement',
        supplier_id=next_supplier_framework["supplierId"],
        framework_slug=next_supplier_framework["frameworkSlug"],
        next_status=status,
    ))
