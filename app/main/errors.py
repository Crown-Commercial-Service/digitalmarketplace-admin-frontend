from dmapiclient import APIError
from flask import render_template
from dmutils.errors import render_error_page

from app.main import main


@main.app_errorhandler(APIError)
def api_error_handler(e):
    return render_error_page(status_code=e.status_code)


@main.app_errorhandler(403)
def page_forbidden(e):
    # Use custom template rather than redirecting to login
    return render_template("errors/403.html"), 403
