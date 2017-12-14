from flask import abort


def get_framework_or_404(client, framework_slug, allowed_statuses=None):
    if allowed_statuses is None:
        allowed_statuses = ['open', 'pending', 'standstill', 'live']

    framework = client.get_framework(framework_slug)['frameworks']

    if allowed_statuses and framework['status'] not in allowed_statuses:
        abort(404)

    return framework
