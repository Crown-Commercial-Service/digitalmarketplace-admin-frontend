from functools import wraps

from flask import abort
from flask_login import current_user


def role_required(*roles):
    """Ensure that logged in user has one of the required roles.

    Return 403 if the user doesn't have a required role.

    Should be applied before the `@login_required` decorator:

        @login_required
        @role_required('admin', 'admin-ccs')
        def view():
            ...

    """

    def role_decorator(func):
        @wraps(func)
        def decorated_view(*args, **kwargs):
            if not any(current_user.has_role(role) for role in roles):
                return abort(403, "One of {} roles required".format(", ".join(roles)))
            return func(*args, **kwargs)

        return decorated_view

    return role_decorator
