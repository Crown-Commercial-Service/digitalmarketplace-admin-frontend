from flask import jsonify, current_app, json
from requests.exceptions import ConnectionError

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

    try:
        api_response = service_loader.status()

        if api_response.status_code is 200:

            return jsonify(status="ok",
                           app_version=utils.get_version_label(),
                           api_status=json.loads(
                               api_response.get_data()
                           )['status'])

    except ConnectionError:
        pass

    current_app.logger.error("Cannot connect to API.")
    return jsonify(status="error", message="Cannot connect to API"), 500
