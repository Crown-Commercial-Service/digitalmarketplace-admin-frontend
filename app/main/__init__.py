from flask import Blueprint
from .helpers.auth import requires_auth

main = Blueprint('main', __name__)

main.before_request(requires_auth)

from . import views
from . import errors
