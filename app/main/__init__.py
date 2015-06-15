from flask import Blueprint


main = Blueprint('main', __name__)

from . import views, activity
from . import errors
