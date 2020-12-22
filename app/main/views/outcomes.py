from datetime import datetime

from flask import Response, abort, current_app, redirect

from dmutils import csv_generator, s3
from dmutils.documents import get_signed_url

from .. import main
from ..auth import role_required
from ... import data_api_client


@main.route('/direct-award/outcomes', methods=['GET'])
@role_required('admin-ccs-category', 'admin-framework-manager', 'admin-ccs-sourcing')
def download_direct_award_outcomes():
    download_filename = "direct-award-outcomes-{}.csv".format(datetime.utcnow().strftime('%Y-%m-%d-at-%H-%M-%S'))
    projects = data_api_client.find_direct_award_projects(having_outcome=True, with_users=True).get('projects', [])
    headers = [
        'ID',
        'Name',
        'Submitted at',
        'Result',
        'Award service ID',
        'Award service name',
        'Award supplier id',
        'Award supplier name',
        'Award value',
        'Awarding organisation name',
        'Award start date',
        'Award end date',
        'User id',
        'User name',
        'User email',
    ]

    formatted_rows = []
    formatted_rows.append(headers)   # add header row
    for project in projects:
        if project['outcome']['result'] != 'awarded':
            continue

        awardDetails = project['outcome']['award']
        resultOfDirectAward = project['outcome']['resultOfDirectAward']
        service = data_api_client.get_archived_service(
            archived_service_id=resultOfDirectAward['archivedService']['id']
        )['services']

        user = project['users'][0]

        row = [
            project['id'],  # id
            project['name'],  # name
            project['outcome']['completedAt'],  # 'Submitted at',
            project['outcome']['result'],  # 'result',
            resultOfDirectAward['archivedService']['service']['id'],  # 'Award service',
            service['serviceName'],  # 'Award service name',
            service['supplierId'],  # 'Award supplier id',
            service['supplierName'],  # 'Award supplier name',
            awardDetails['awardValue'],   # 'awardValue',
            awardDetails['awardingOrganisationName'],  # 'awardingOrganisationName',
            awardDetails['startDate'],  # 'awardStartDate',
            awardDetails['endDate'],  # 'awardEndDate',
            user['id'],  # 'User id',
            user['name'],  # 'User name',
            user['emailAddress'],  # 'User email',
        ]
        formatted_rows.append(row)

    return Response(
        csv_generator.iter_csv(formatted_rows),
        mimetype='text/csv',
        headers={
            "Content-Disposition": "attachment;filename={}".format(download_filename),
            "Content-Type": "text/csv; header=present"
        }
    )


@main.route("/digital-outcomes-and-specialists/outcomes", methods=["GET"])
@role_required("admin-ccs-category", "admin-framework-manager", "admin-ccs-sourcing")
def download_dos_outcomes():
    # get the slug for the latest DOS framework iteration
    framework_slug = (
        sorted(
            filter(
                lambda fw: (
                    fw["family"] == "digital-outcomes-and-specialists"
                    and fw["status"] == "live"
                ),
                data_api_client.find_frameworks()["frameworks"]
            ),
            key=lambda fw: fw["frameworkLiveAtUTC"],
            reverse=True,
        )[0]["slug"]
    )

    reports_bucket = s3.S3(current_app.config["DM_REPORTS_BUCKET"])
    url = get_signed_url(
        reports_bucket,
        f"{framework_slug}/reports/opportunity-data.csv",
        current_app.config["DM_ASSETS_URL"]
    )

    if not url:
        abort(404)

    return redirect(url)
