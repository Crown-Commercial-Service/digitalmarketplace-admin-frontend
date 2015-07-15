from flask import jsonify, current_app, request

from .. import data_api_client
from . import status
from dmutils.status import get_flags


@status.route('/_status')
def status():

    if 'ignore-dependencies' in request.args:
        return jsonify(
            status="ok",
        ), 200

    version = current_app.config['VERSION']
    status = data_api_client.get_status()

    if status['status'] == "ok":
        return jsonify(
            status="ok",
            version=version,
            api_status=status,
            flags=get_flags(current_app)
        )

    return jsonify(
        status="error",
        version=version,
        api_status=status,
        message="Error connecting to the (Data) API.",
        flags=get_flags(current_app)
    ), 500
