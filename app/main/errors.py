from flask import render_template
from app.main import main
from dmutils.apiclient import APIError


@main.app_errorhandler(APIError)
def api_error(e):
    return _render_error_template(e.status_code)


@main.app_errorhandler(400)
def bad_request(e):
    return _render_error_template(400)


@main.app_errorhandler(404)
def page_not_found(e):
    return _render_error_template(404)


@main.app_errorhandler(500)
def exception(e):
    return _render_error_template(500)


@main.app_errorhandler(503)
def service_unavailable(e):
    return _render_error_template(503)


def _render_error_template(status_code):
    return render_template(
        _get_template(status_code),
        **main.config['BASE_TEMPLATE_DATA']
    ), status_code


def _get_template(status_code):
    if status_code == 404:
        return "errors/404.html"
    else:
        return "errors/500.html"
