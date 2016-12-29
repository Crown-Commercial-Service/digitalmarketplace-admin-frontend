from functools import wraps
from lxml import html
import mock
try:
    from urlparse import urlsplit
except ImportError:
    from urllib.parse import urlsplit

from dmutils.user import User

from ...helpers import BaseApplicationTest, LoggedInApplicationTest


def user_data(role='admin'):
    return {
        'users': {
            'id': 12345,
            'emailAddress': 'valid@example.com',
            'role': role,
            'locked': False,
            'active': True,
            'name': "tester"
        }
    }


class TestLogin(BaseApplicationTest):
    def test_should_be_redirected_to_login_page(self):
        res = self.client.get('/admin')
        assert res.status_code == 302
        assert urlsplit(res.location).path == '/admin/login'

    def test_should_show_login_page(self):
        res = self.client.get("/admin/login")
        assert res.status_code == 200
        assert "Administrator login" in res.get_data(as_text=True)

    @mock.patch('app.data_api_client')
    @mock.patch('app.main.views.login.data_api_client')
    def test_valid_login(self, login_data_api_client, init_data_api_client):
        login_data_api_client.authenticate_user.return_value = user_data()
        init_data_api_client.get_user.return_value = user_data()
        res = self.client.post('/admin/login', data={
            'email_address': 'valid@email.com',
            'password': '1234567890'
        })
        assert res.status_code == 302

        res = self.client.get('/admin')
        assert res.status_code == 200

    @mock.patch('app.main.views.login.data_api_client')
    def test_should_strip_whitespace_surrounding_login_email_address_field(self, data_api_client):
        data_api_client.authenticate_user.return_value = user_data()
        self.client.post("/admin/login", data={
            'email_address': '  valid@email.com  ',
            'password': '1234567890'
        })
        data_api_client.authenticate_user.assert_called_with('valid@email.com', '1234567890')

    @mock.patch('app.main.views.login.data_api_client')
    def test_should_not_strip_whitespace_surrounding_login_password_field(self, data_api_client):
        data_api_client.authenticate_user.return_value = user_data()
        self.client.post("/admin/login", data={
            'email_address': 'valid@email.com',
            'password': '  1234567890  '
        })
        data_api_client.authenticate_user.assert_called_with('valid@email.com', '  1234567890  ')

    @mock.patch('app.main.views.login.data_api_client')
    def test_ok_next_url_redirects_on_login(self, data_api_client):
        data_api_client.authenticate_user.return_value = user_data()
        res = self.client.post('/admin/login?next=/admin/safe', data={
            'email_address': 'valid@example.com',
            'password': '1234567890',
        })
        assert res.status_code == 302
        assert urlsplit(res.location).path == '/admin/safe'

    @mock.patch('app.main.views.login.data_api_client')
    def test_bad_next_url_takes_user_to_dashboard(self, data_api_client):
        data_api_client.authenticate_user.return_value = user_data()
        res = self.client.post('/admin/login?next=http://badness.com', data={
            'email_address': 'valid@example.com',
            'password': '1234567890',
        })
        assert res.status_code == 302
        assert urlsplit(res.location).path == '/admin'

    @mock.patch('app.main.views.login.data_api_client')
    def test_should_have_cookie_on_redirect(self, data_api_client):
        data_api_client.authenticate_user.return_value = user_data()
        with self.app.app_context():
            self.app.config['SESSION_COOKIE_DOMAIN'] = '127.0.0.1'
            self.app.config['SESSION_COOKIE_SECURE'] = True
            res = self.client.post('/admin/login', data={
                'email_address': 'valid@example.com',
                'password': '1234567890',
            })
            cookie_parts = res.headers['Set-Cookie'].split('; ')
            assert 'Secure' in cookie_parts
            assert 'HttpOnly' in cookie_parts
            assert 'Path=/admin' in cookie_parts

    @mock.patch('app.data_api_client')
    @mock.patch('app.main.views.login.data_api_client')
    def test_should_redirect_to_login_on_logout(self, login_data_api_client, init_data_api_client):
        login_data_api_client.authenticate_user.return_value = user_data()
        init_data_api_client.get_user.return_value = user_data()
        self.client.post('/admin/login', data={
            'email_address': 'valid@example.com',
            'password': '1234567890',
        })
        res = self.client.get('/admin/logout')
        assert res.status_code == 302
        assert urlsplit(res.location).path == '/admin/login'

    @mock.patch('app.data_api_client')
    @mock.patch('app.main.views.login.data_api_client')
    def test_logout_should_log_user_out(self, login_data_api_client, init_data_api_client):
        login_data_api_client.authenticate_user.return_value = user_data()
        init_data_api_client.get_user.return_value = user_data()
        self.client.post('/admin/login', data={
            'email_address': 'valid@example.com',
            'password': '1234567890',
        })
        self.client.get('/admin/logout')
        res = self.client.get('/admin')
        assert res.status_code == 302
        assert urlsplit(res.location).path == '/admin/login'

    @mock.patch('app.main.views.login.data_api_client')
    def test_should_return_a_403_for_invalid_login(self, data_api_client):
        data_api_client.authenticate_user.return_value = None

        res = self.client.post('/admin/login', data={
            'email_address': 'valid@example.com',
            'password': '1234567890',
        })

        assert res.status_code == 403

    @mock.patch('app.main.views.login.data_api_client')
    def test_should_return_a_403_if_invalid_role(self, data_api_client):
        data_api_client.authenticate_user.return_value = user_data(role='supplier')

        res = self.client.post('/admin/login', data={
            'email_address': 'valid@example.com',
            'password': '1234567890',
        })

        assert res.status_code == 403

    @mock.patch('app.main.views.login.data_api_client')
    def test_can_login_with_admin_ccs_role(self, data_api_client):
        data_api_client.authenticate_user.return_value = user_data(role='admin-ccs-category')

        res = self.client.post('/admin/login', data={
            'email_address': 'valid@example.com',
            'password': '1234567890',
        })

        assert res.status_code == 302

    def test_should_be_validation_error_if_no_email_or_password(self):
        res = self.client.post('/admin/login', data={})
        assert res.status_code == 400

    def test_should_be_validation_error_if_invalid_email(self):
        res = self.client.post('/admin/login', data={
            'email_address': 'invalid',
            'password': '1234567890',
        })
        assert res.status_code == 400


class TestSession(BaseApplicationTest):
    def test_url_with_non_canonical_trailing_slash(self):
        response = self.client.get('/admin/')
        assert response.status_code == 301
        assert response.location == "http://localhost/admin"


class TestLoginFormsNotAutofillable(BaseApplicationTest):

    def _forms_and_inputs_not_autofillable(
            self, url, expected_title
    ):
        response = self.client.get(url)
        assert response.status_code == 200

        document = html.fromstring(response.get_data(as_text=True))

        page_title = document.xpath(
            '//h1/text()')[0].strip()
        assert page_title == expected_title

        forms = document.xpath('//div[@class="page-container"]//form')

        for form in forms:
            assert form.get('autocomplete') == "off"
            non_hidden_inputs = form.xpath('//input[@type!="hidden"]')

            for input in non_hidden_inputs:
                assert input.get('autocomplete') == "off"

    def test_login_form_and_inputs_not_autofillable(self):
        self._forms_and_inputs_not_autofillable(
            "/admin/login",
            "Administrator login"
        )


class TestRoleRequired(LoggedInApplicationTest):
    def user_loader(self, user_id):
        if user_id:
            return User(
                user_id, 'test@example.com', None, None, False, True, 'tester', 'admin-ccs-category'
            )

    def test_admin_ccs_can_view_admin_dashboard(self):
        response = self.client.get('/admin')
        assert response.status_code == 200

    def test_admin_role_required_service_status_edit(self):
        response = self.client.post('/admin/services/status/1')
        assert response.status_code == 403

    def test_admin_role_required_audit_acknowledge(self):
        response = self.client.post('/admin/service-updates/1/acknowledge')
        assert response.status_code == 403

    def test_admin_role_required_unlock_user(self):
        response = self.client.post('/admin/suppliers/users/1/unlock')
        assert response.status_code == 403

    def test_admin_role_required_activate_user(self):
        response = self.client.post('/admin/suppliers/users/1/activate')
        assert response.status_code == 403

    def test_admin_role_required_deactivate_user(self):
        response = self.client.post('/admin/suppliers/users/1/deactivate')
        assert response.status_code == 403

    def test_admin_role_required_invite_user(self):
        response = self.client.post('/admin/suppliers/1/invite-user')
        assert response.status_code == 403
