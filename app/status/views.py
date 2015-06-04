from flask import jsonify, current_app

from .. import data_api_client
from . import status
from dmutils.status import get_version_label, get_flags


@status.route('/_status')
def status():

    status = data_api_client.get_status()

    if status['status'] == "ok":
        return jsonify(
            status="ok",
            version=get_version_label(),
            api_status=status,
            flags=get_flags(current_app)
        )

    return jsonify(
        status="error",
        version=get_version_label(),
        api_status=status,
        message="Error connecting to the (Data) API.",
        flags=get_flags(current_app)
    ), 500
