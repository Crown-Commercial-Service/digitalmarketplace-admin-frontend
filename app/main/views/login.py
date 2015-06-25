from flask import request, render_template, url_for, redirect, session

from .. import main
from ..helpers.auth import check_auth
from . import get_template_data


@main.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'GET':
        return render_template("login.html", **get_template_data({
            "previous_responses": None,
            "logged_out": "logged_out" in request.args
        }))
    if check_auth(
        request.form['username'],
        request.form['password'],
        main.config['PASSWORD_HASH']
    ):
        session['username'] = request.form['username']
        return redirect(url_for('.index'))

    return render_template("login.html", **get_template_data({
        "error": "Could not log in",
        "previous_responses": request.form
    }))


@main.route('/logout', methods=['GET'])
def logout():
    session.pop('username', None)
    return redirect(url_for('.login', logged_out=''))
