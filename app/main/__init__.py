from flask import Blueprint


main = Blueprint('main', __name__)

from .views import agreements, communications, service_updates, services, suppliers, stats, users, buyers
from app.main import errors


@main.after_request
def add_cache_control(response):
    response.cache_control.no_cache = True
    return response
