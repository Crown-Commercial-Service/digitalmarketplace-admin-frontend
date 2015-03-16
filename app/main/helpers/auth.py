import os
import base64
from flask import request, Response
from pbkdf2 import crypt


def check_auth(username, password):
    """This function is called to check if a username /
    password combination is valid.
    """
    secret = base64.b64decode(os.getenv('DM_ADMIN_FRONTEND_PASSWORD_HASH'))
    return secret == crypt(username + password, secret, iterations=10000)


def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'}
    )


def requires_auth():
    auth = request.authorization
    if not auth or not check_auth(auth.username, auth.password):
        return authenticate()
