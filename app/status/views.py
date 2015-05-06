from flask import jsonify

from .. import data_api_client
from . import status
from . import utils


@status.route('/_status')
def status():

    status = data_api_client.get_status()

    if status['status'] == "ok":
        return jsonify(
            status="ok",
            version=utils.get_version_label(),
            api_status=status,
        )

    return jsonify(
        status="error",
        version=utils.get_version_label(),
        api_status=status,
        message="Error connecting to the (Data) API.",
    ), 500
