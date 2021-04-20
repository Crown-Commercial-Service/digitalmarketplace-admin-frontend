import datetime
import re


def filter_relevant_frameworks(frameworks):
    """
    Show admins only the frameworks that they're likely to be interested in.

    Include all live frameworks. Include all expired DOS frameworks, but only the last 2 expired G-Cloud frameworks.
    """
    frameworks.sort(key=lambda x: x['id'], reverse=True)

    expired_gcloud_frameworks = 0

    for framework in frameworks:
        if framework['status'] == 'coming':
            continue

        if framework["family"] == 'digital-outcomes-and-specialists':
            yield framework
        elif framework['status'] != 'expired':
            yield framework
        elif framework['status'] == 'expired' and expired_gcloud_frameworks < 2:
            expired_gcloud_frameworks += 1
            yield framework


def parse_document_upload_time(data):
    match = re.search(r"(\d{4}-\d{2}-\d{2}-\d{2}\d{2})\..{2,3}$", data)
    if match:
        return datetime.strptime(match.group(1), "%Y-%m-%d-%H%M")
