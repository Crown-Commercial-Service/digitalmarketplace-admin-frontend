from flask import Blueprint


main = Blueprint('main', __name__)

from .views import login, agreements, communications, service_updates, services, suppliers, stats, users, buyers
from app.main import errors
