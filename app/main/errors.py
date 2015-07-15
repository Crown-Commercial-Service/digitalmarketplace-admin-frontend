from flask import render_template
from . import main


@main.app_errorhandler(404)
def page_not_found(e):
    return render_template("errors/404.html",
                           **main.config['BASE_TEMPLATE_DATA']), 404


@main.app_errorhandler(500)
def exception(e):
    return render_template("errors/500.html",
                           **main.config['BASE_TEMPLATE_DATA']), 500


@main.app_errorhandler(503)
def service_unavailable(e):
    return render_template("errors/500.html",
                           **main.config['BASE_TEMPLATE_DATA']), 503
