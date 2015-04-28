from flask import jsonify
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
                           api_status=api_response.json()['status']
                           )

    except ConnectionError:
        pass

    return utils.return_500_if_problem_with_api()
