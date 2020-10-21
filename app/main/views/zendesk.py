from .. import main
from flask import render_template, Response, url_for
from flask_login import current_user
from ... import data_api_client


def _user_info(email):
    user = data_api_client.get_user(email_address=email)
    supplier = None
    if user:
        user = user.get('users')
        if user['role'] == 'supplier':
            supplier = data_api_client.get_supplier(user['supplier_code'])['supplier']
    return user, supplier


@main.route('/zendesk', methods=['GET'])
@main.route('/zendesk/<email>', methods=['GET'])
def zendesk(email=None):
    resp = Response()
    resp.headers['X-Frame-Options'] = 'ALLOW-FROM https://marketplace1.zendesk.com/'
    if not current_user.is_authenticated or not current_user.has_role('admin'):
        resp.data = "<a href='"+url_for('main.render_login')+"' target='_blank'>Please login</a> then refresh!"
    else:
        if email:
            user, supplier = _user_info(email)
            resp.data = render_template('zendesk/zendesk_result.html', email=email, user=user, supplier=supplier)
        else:
            resp.data = render_template('zendesk/zendesk_loader.html')
    return resp
