from flask import render_template
from app.main import main


@main.app_errorhandler(400)
def bad_request(e):
    return render_template("errors/500.html",
                           **main.config['BASE_TEMPLATE_DATA']), 400


@main.app_errorhandler(404)
def page_not_found(e):
    return render_template("errors/404.html",
                           **main.config['BASE_TEMPLATE_DATA']), 404


@main.app_errorhandler(403)
def page_not_found(e):
    return render_template("errors/403.html",
                           **main.config['BASE_TEMPLATE_DATA']), 403


@main.app_errorhandler(500)
def exception(e):
    return render_template("errors/500.html",
                           **main.config['BASE_TEMPLATE_DATA']), 500


@main.app_errorhandler(503)
def service_unavailable(e):
    return render_template("errors/500.html",
                           **main.config['BASE_TEMPLATE_DATA']), 503
