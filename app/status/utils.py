import os
from flask import jsonify, current_app


def get_version_label():
    try:
        path = os.path.join(os.path.dirname(__file__),
                            '..', '..', 'version_label')
        with open(path) as f:
            return f.read().strip()
    except IOError:
        return None


def return_500_if_problem_with_api():

    current_app.logger.exception("Cannot connect to API.")
    return jsonify(status="error", message="Cannot connect to API"), 500
