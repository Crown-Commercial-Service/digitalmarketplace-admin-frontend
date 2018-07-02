from flask import Blueprint, current_app
from flask_login import current_user, login_required


main = Blueprint('main', __name__)
public = Blueprint('public', __name__)  # Admin login not required

from .views import (
    agreements, communications, direct_award, search, service_updates,
    services, suppliers, stats, users, buyers, admin_manager
)
from app.main import errors


@main.before_request
@login_required
def require_login():
    if current_user.is_authenticated() and not current_user.role.startswith('admin'):
        return current_app.login_manager.unauthorized()


@main.after_request
def add_cache_control(response):
    response.cache_control.no_cache = True
    return response
