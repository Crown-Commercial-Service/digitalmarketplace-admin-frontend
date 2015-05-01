from flask import jsonify, current_app

from . import status
from . import utils
from ..main.helpers.service import ServiceLoader
from ..main import main


@status.route('/_status')
def status():

    # ServiceLoader is the only thing that actually connects to the API
    service_loader = ServiceLoader(
        main.config['API_URL'],
        main.config['API_AUTH_TOKEN']
    )

    api_response = utils.return_response_from_api_status_call(
        service_loader.status
    )

    apis_with_errors = []

    if api_response is None or api_response.status_code != 200:
        apis_with_errors.append("(Data) API")

    # if no errors found, return everything
    if not apis_with_errors:
        return jsonify(
            status="ok",
            version=utils.get_version_label(),
            api_status=api_response.json(),
        )

    message = "Error connecting to the " \
              + (" and the ".join(apis_with_errors)) \
              + "."

    current_app.logger.error(message)

    return jsonify(
        status="error",
        version=utils.get_version_label(),
        api_status=utils.return_json_or_none(api_response),
        message=message,
    ), 500
