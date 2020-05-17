from flask import request, render_template, url_for, redirect, \
    current_app, flash
from flask_login import login_user, logout_user, login_required
from dmutils.user import user_has_role, User

from .. import main
from ... import data_api_client
from ..forms import LoginForm


@main.route('/login', methods=['GET'])
def render_login():
    form = LoginForm()
    return render_template('login.html', form=form)


@main.route('/login', methods=['POST'])
def process_login():
    next_url = request.args.get('next')
    form = LoginForm(request.form)
    if form.validate():
        user_json = data_api_client.authenticate_user(
            form.email_address.data,
            form.password.data
            )

        if not any(user_has_role(user_json, role) for
           role in ['assessor', 'admin', 'admin-ccs-category', 'admin-ccs-sourcing']):
                message = "login.fail: Failed to log in: %s"
                current_app.logger.info(message, form.email_address.data)
                flash('no_account', 'error')
                return render_template(
                    'login.html',
                    form=form,
                    next=next_url
                ), 403

        user = User.from_json(user_json)
        login_user(user)
        current_app.logger.info('login.success')

        if next_url and next_url.startswith('/admin'):
            return redirect(next_url)

        return redirect(url_for('.index'))
    else:
        return render_template(
            'login.html',
            form=form
        ), 400


@main.route('/logout', methods=['GET'])
@login_required
def logout():
    logout_user()
    flash('logged_out', 'success')
    return redirect(url_for('.render_login'))
