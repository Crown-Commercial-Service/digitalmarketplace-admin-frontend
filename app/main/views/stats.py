from urllib.parse import urljoin

from flask import abort, current_app, redirect

from .. import public


@public.route('/statistics/<string:framework_slug>', methods=['GET'])
def view_statistics(framework_slug):
    pp_id = current_app.config["PERFORMANCE_PLATFORM_ID_MAPPING"].get(framework_slug.lower())

    if not pp_id:
        abort(410)
    else:
        return redirect(urljoin(current_app.config["PERFORMANCE_PLATFORM_BASE_URL"], pp_id), code=301)
