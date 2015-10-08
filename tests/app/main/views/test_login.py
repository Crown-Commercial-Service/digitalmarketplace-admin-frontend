from functools import wraps
from lxml import html
from nose.tools import assert_equal, assert_in
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
        assert_equal(res.status_code, 302)
        assert_equal(urlsplit(res.location).path, '/admin/login')

    def test_should_show_login_page(self):
        res = self.client.get("/admin/login")
        assert_equal(res.status_code, 200)
        assert_in("Administrator login", res.get_data(as_text=True))

    @mock.patch('app.main.views.login.data_api_client')
    def test_valid_login(self, apiclient):
        apiclient.authenticate_user.return_value = user_data()
        res = self.client.post('/admin/login', data={
            'email_address': 'valid@email.com',
            'password': '1234567890'
        })
        assert_equal(res.status_code, 302)

        res = self.client.get('/admin')
        assert_equal(res.status_code, 200)

    @mock.patch('app.main.views.login.data_api_client')
    def test_should_strip_whitespace_surrounding_login_email_address_field(self, apiclient):
        apiclient.authenticate_user.return_value = user_data()
        self.client.post("/admin/login", data={
            'email_address': '  valid@email.com  ',
            'password': '1234567890'
        })
        apiclient.authenticate_user.assert_called_with('valid@email.com', '1234567890', supplier=False)

    @mock.patch('app.main.views.login.data_api_client')
    def test_should_not_strip_whitespace_surrounding_login_password_field(self, apiclient):
        apiclient.authenticate_user.return_value = user_data()
        self.client.post("/admin/login", data={
            'email_address': 'valid@email.com',
            'password': '  1234567890  '
        })
        apiclient.authenticate_user.assert_called_with('valid@email.com', '  1234567890  ', supplier=False)

    @mock.patch('app.main.views.login.data_api_client')
    def test_ok_next_url_redirects_on_login(self, apiclient):
        apiclient.authenticate_user.return_value = user_data()
        res = self.client.post('/admin/login?next=/admin/safe', data={
            'email_address': 'valid@example.com',
            'password': '1234567890',
        })
        assert_equal(res.status_code, 302)
        assert_equal(urlsplit(res.location).path, '/admin/safe')

    @mock.patch('app.main.views.login.data_api_client')
    def test_bad_next_url_takes_user_to_dashboard(self, apiclient):
        apiclient.authenticate_user.return_value = user_data()
        res = self.client.post('/admin/login?next=http://badness.com', data={
            'email_address': 'valid@example.com',
            'password': '1234567890',
        })
        assert_equal(res.status_code, 302)
        assert_equal(urlsplit(res.location).path, '/admin')

    @mock.patch('app.main.views.login.data_api_client')
    def test_should_have_cookie_on_redirect(self, apiclient):
        apiclient.authenticate_user.return_value = user_data()
        with self.app.app_context():
            self.app.config['SESSION_COOKIE_DOMAIN'] = '127.0.0.1'
            self.app.config['SESSION_COOKIE_SECURE'] = True
            res = self.client.post('/admin/login', data={
                'email_address': 'valid@example.com',
                'password': '1234567890',
            })
            cookie_parts = res.headers['Set-Cookie'].split('; ')
            assert_in('Secure', cookie_parts)
            assert_in('HttpOnly', cookie_parts)
            assert_in('Path=/admin', cookie_parts)

    @mock.patch('app.main.views.login.data_api_client')
    def test_should_redirect_to_login_on_logout(self, apiclient):
        apiclient.authenticate_user.return_value = user_data()
        self.client.post('/admin/login', data={
            'email_address': 'valid@example.com',
            'password': '1234567890',
        })
        res = self.client.get('/admin/logout')
        assert_equal(res.status_code, 302)
        assert_equal(urlsplit(res.location).path, '/admin/login')

    @mock.patch('app.main.views.login.data_api_client')
    def test_logout_should_log_user_out(self, apiclient):
        apiclient.authenticate_user.return_value = user_data()
        self.client.post('/admin/login', data={
            'email_address': 'valid@example.com',
            'password': '1234567890',
        })
        self.client.get('/admin/logout')
        res = self.client.get('/admin')
        assert_equal(res.status_code, 302)
        assert_equal(urlsplit(res.location).path, '/admin/login')

    @mock.patch('app.main.views.login.data_api_client')
    def test_should_return_a_403_for_invalid_login(self, data_api_client):
        data_api_client.authenticate_user.return_value = None

        res = self.client.post('/admin/login', data={
            'email_address': 'valid@example.com',
            'password': '1234567890',
        })

        assert_equal(res.status_code, 403)

    @mock.patch('app.main.views.login.data_api_client')
    def test_should_return_a_403_if_invalid_role(self, data_api_client):
        data_api_client.authenticate_user.return_value = user_data(role='supplier')

        res = self.client.post('/admin/login', data={
            'email_address': 'valid@example.com',
            'password': '1234567890',
        })

        assert_equal(res.status_code, 403)

    @mock.patch('app.main.views.login.data_api_client')
    def test_can_login_with_admin_ccs_role(self, data_api_client):
        data_api_client.authenticate_user.return_value = user_data(role='admin-ccs-category')

        res = self.client.post('/admin/login', data={
            'email_address': 'valid@example.com',
            'password': '1234567890',
        })

        assert_equal(res.status_code, 302)

    def test_should_be_validation_error_if_no_email_or_password(self):
        res = self.client.post('/admin/login', data={})
        assert_equal(res.status_code, 400)

    def test_should_be_validation_error_if_invalid_email(self):
        res = self.client.post('/admin/login', data={
            'email_address': 'invalid',
            'password': '1234567890',
        })
        assert_equal(res.status_code, 400)


class TestSession(BaseApplicationTest):
    def test_url_with_non_canonical_trailing_slash(self):
        response = self.client.get('/admin/')
        self.assertEquals(301, response.status_code)
        self.assertEquals("http://localhost/admin", response.location)


class TestLoginFormsNotAutofillable(BaseApplicationTest):

    def _forms_and_inputs_not_autofillable(
            self, url, expected_title
    ):
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

        document = html.fromstring(response.get_data(as_text=True))

        page_title = document.xpath(
            '//div[@class="page-container"]//h1/text()')[0].strip()
        self.assertEqual(expected_title, page_title)

        forms = document.xpath('//div[@class="page-container"]//form')

        for form in forms:
            self.assertEqual("off", form.get('autocomplete'))
            non_hidden_inputs = form.xpath('//input[@type!="hidden"]')

            for input in non_hidden_inputs:
                self.assertEqual("off", input.get('autocomplete'))

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
        assert_equal(200, response.status_code)

    def test_admin_role_required_service_section_view(self):
        response = self.client.get('/admin/services/1/edit/documents')
        assert_equal(403, response.status_code)

    def test_admin_role_required_service_section_edit(self):
        response = self.client.post('/admin/services/1/edit/documents')
        assert_equal(403, response.status_code)

    def test_admin_role_required_service_status_edit(self):
        response = self.client.post('/admin/services/status/1')
        assert_equal(403, response.status_code)

    def test_admin_role_required_audit_acknowledge(self):
        response = self.client.post('/admin/service-updates/1/acknowledge')
        assert_equal(403, response.status_code)

    def test_admin_role_required_unlock_user(self):
        response = self.client.post('/admin/suppliers/users/1/unlock')
        assert_equal(403, response.status_code)

    def test_admin_role_required_activate_user(self):
        response = self.client.post('/admin/suppliers/users/1/activate')
        assert_equal(403, response.status_code)

    def test_admin_role_required_deactivate_user(self):
        response = self.client.post('/admin/suppliers/users/1/deactivate')
        assert_equal(403, response.status_code)

    def test_admin_role_required_invite_user(self):
        response = self.client.post('/admin/suppliers/1/invite-user')
        assert_equal(403, response.status_code)
