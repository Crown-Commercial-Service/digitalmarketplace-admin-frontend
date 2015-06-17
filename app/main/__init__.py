from flask import Blueprint


main = Blueprint('main', __name__)

from . import views, service_update_audits
from . import errors
