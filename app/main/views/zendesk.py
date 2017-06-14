from .. import main
from flask import render_template, Response, url_for
from flask_login import current_user
from ... import data_api_client


@main.route('/zendesk', methods=['GET'])
@main.route('/zendesk/<email>', methods=['GET'])
def zendesk(email=None):
    resp = Response()
    resp.headers['X-Frame-Options'] = 'ALLOW-FROM https://marketplace1.zendesk.com/'
    if not current_user.is_authenticated or not current_user.has_role('admin'):
        resp.data = "<A href='"+url_for('main.render_login')+"' target='_blank'>Please login</a> then refresh!"
    else:
        if email:
            user = data_api_client.get_user(email_address=email)
            if user:
                user = user.get('users')
            teammembers = data_api_client.req.teammembers(email.split('@')[-1]).get()
            if user['role'] == 'applicant' or user['role'] == 'supplier':
                for tm in teammembers['teammembers']:
                    u = data_api_client.get_user(user_id=tm['id'])
                    tm['application_id'] = u.get('users').get('application_id')
            supplier = None
            application = None
            briefs = None
            if user:
                if user['role'] == 'supplier':
                    supplier = data_api_client.get_supplier(user['supplier_code'])['supplier']
                if user['role'] == 'buyer':
                    briefs = data_api_client.find_briefs(user['id']).get('briefs', [])
            resp.data = render_template('zendesk/zendesk_result.html', email=email, user=user, supplier=supplier,
                                        teammembers=teammembers, applications=application, briefs=briefs)
        else:
            resp.data = render_template('zendesk/zendesk_loader.html')
    return resp
