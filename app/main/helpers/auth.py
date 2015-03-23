import os
import base64
from flask import redirect, request, session
from pbkdf2 import crypt


def check_auth(username, password):
    """This function is called to check if a username /
    password combination is valid.
    """
    secret = base64.b64decode(
        os.getenv('DM_ADMIN_FRONTEND_PASSWORD_HASH')
    ).decode('utf-8')
    return secret == crypt(username + password, secret, iterations=10000)


def requires_auth():
    if (
        'username' not in session and
        request.endpoint != 'main.login' and
        request.endpoint != 'static'
    ):
        return redirect("/login")


def is_authenticated():
    return 'username' in session
