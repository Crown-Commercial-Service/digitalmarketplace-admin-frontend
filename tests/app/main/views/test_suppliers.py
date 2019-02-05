import io
try:
    from urlparse import urlsplit
    from StringIO import StringIO
except ImportError:
    from urllib.parse import urlsplit
    from io import BytesIO as StringIO
import mock
import pytest
from lxml import html
from nose.tools import eq_
from nose.tools import assert_equals
from dmapiclient import HTTPError, APIError
from dmutils.email import EmailError
from dmutils.forms import FakeCsrf
from dmapiclient.audit import AuditTypes
from ...helpers import LoggedInApplicationTest, Response


@mock.patch('app.main.views.suppliers.data_api_client')
class TestSuppliersListView(LoggedInApplicationTest):

    def test_should_raise_http_error_from_api(self, data_api_client):
        data_api_client.find_suppliers.side_effect = HTTPError(Response(404))
        response = self.client.get('/admin/suppliers')
        assert_equals(response.status_code, 404)

    def test_should_list_suppliers(self, data_api_client):
        data_api_client.find_suppliers.return_value = {
            'suppliers': [
                {'code': 1234, 'name': 'Supplier 1'},
                {'code': 1235, 'name': 'Supplier 2'},
            ]
        }
        response = self.client.get("/admin/suppliers")
        document = html.fromstring(response.get_data(as_text=True))

        assert_equals(response.status_code, 200)
        assert_equals(len(document.cssselect('.summary-item-row')), 2)

    def test_should_search_by_prefix(self, data_api_client):
        data_api_client.find_suppliers.side_effect = HTTPError(Response(404))
        self.client.get("/admin/suppliers?supplier_name_prefix=foo&per_page=1000")

        data_api_client.find_suppliers.assert_called_once_with(prefix='foo', per_page=1000)

    def test_should_find_by_supplier_code(self, data_api_client):
        data_api_client.get_supplier.side_effect = HTTPError(Response(404))
        self.client.get('/admin/suppliers?supplier_code=12345')

        data_api_client.get_supplier.assert_called_once_with("12345")


class TestSupplierUsersView(LoggedInApplicationTest):

    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_404_if_no_supplier_does_not_exist(self, data_api_client):
        data_api_client.get_supplier.side_effect = HTTPError(Response(404))
        response = self.client.get('/admin/suppliers/users?supplier_code=999')
        self.assertEquals(404, response.status_code)

    def test_should_404_if_no_supplier_code(self):
        response = self.client.get('/admin/suppliers/users')
        self.assertEquals(404, response.status_code)

    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_call_apis_with_supplier_code(self, data_api_client):
        data_api_client.get_supplier.return_value = self.load_example_listing("supplier_response")
        response = self.client.get('/admin/suppliers/users?supplier_code=1000')

        self.assertEquals(200, response.status_code)

        data_api_client.get_supplier.assert_called_with('1000')
        data_api_client.find_users.assert_called_with('1000')

    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_have_supplier_name_on_page(self, data_api_client):
        data_api_client.get_supplier.return_value = self.load_example_listing("supplier_response")
        response = self.client.get('/admin/suppliers/users?supplier_code=1000')

        self.assertEquals(200, response.status_code)
        self.assertIn(
            'Example Pty Ltd',
            response.get_data(as_text=True)
        )

    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_indicate_if_there_are_no_users(self, data_api_client):
        data_api_client.get_supplier.return_value = self.load_example_listing("supplier_response")
        data_api_client.find_users.return_value = {'users': {}}

        response = self.client.get('/admin/suppliers/users?supplier_code=1000')

        self.assertEquals(200, response.status_code)
        self.assertIn(
            "This supplier has no users on the Digital Marketplace",
            response.get_data(as_text=True)
        )

    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_show_user_details_on_page(self, data_api_client):
        data_api_client.get_supplier.return_value = self.load_example_listing("supplier_response")
        data_api_client.find_users.return_value = self.load_example_listing("users_response")

        response = self.client.get('/admin/suppliers/users?supplier_code=1000')

        self.assertEquals(200, response.status_code)
        self.assertIn(
            "Test User",
            response.get_data(as_text=True)
        )
        self.assertIn(
            "test.user@sme.com",
            response.get_data(as_text=True)
        )
        self.assertIn(
            "19:33",
            response.get_data(as_text=True)
        )
        self.assertIn(
            "23-07-2015",
            response.get_data(as_text=True)
        )
        self.assertIn(
            "22:46",
            response.get_data(as_text=True)
        )
        self.assertIn(
            "29-06-2015",
            response.get_data(as_text=True)
        )
        self.assertIn(
            "No",
            response.get_data(as_text=True)
        )

        self.assertIn(
            '<input type="submit" class="button-destructive"  value="Deactivate"  />',
            response.get_data(as_text=True)
        )

        self.assertIn(
            '<form action="/admin/suppliers/users/999/deactivate" method="post">',
            response.get_data(as_text=True)
        )

        self.assertIn(
            '<button class="button-save">Move user to this supplier</button>',
            response.get_data(as_text=True)
        )

        self.assertIn(
            '<form action="/admin/suppliers/0/move-existing-user" method="post">',
            response.get_data(as_text=True)
        )

    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_show_unlock_button_if_user_locked(self, data_api_client):
        data_api_client.get_supplier.return_value = self.load_example_listing("supplier_response")

        users = self.load_example_listing("users_response")
        users["users"][0]["locked"] = True
        data_api_client.find_users.return_value = users

        response = self.client.get('/admin/suppliers/users?supplier_code=1000')

        self.assertEquals(200, response.status_code)
        self.assertIn(
            '<form action="/admin/suppliers/users/999/unlock" method="post">',
            response.get_data(as_text=True)
        )
        self.assertIn(
            '<input type="submit" class="button-secondary"  value="Unlock"  />',
            response.get_data(as_text=True)
        )

    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_show_activate_button_if_user_deactivated(self, data_api_client):
        data_api_client.get_supplier.return_value = self.load_example_listing("supplier_response")

        users = self.load_example_listing("users_response")
        users["users"][0]["active"] = False
        data_api_client.find_users.return_value = users

        response = self.client.get('/admin/suppliers/users?supplier_code=1000')

        self.assertEquals(200, response.status_code)
        self.assertIn(
            '<form action="/admin/suppliers/users/999/activate" method="post">',
            response.get_data(as_text=True)
        )
        self.assertIn(
            '<input type="submit" class="button-secondary"  value="Activate"  />',
            response.get_data(as_text=True)
        )

    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_call_api_to_unlock_user(self, data_api_client):
        data_api_client.get_supplier.return_value = self.load_example_listing("supplier_response")
        data_api_client.update_user.return_value = self.load_example_listing("user_response")

        response = self.client.post('/admin/suppliers/users/999/unlock', data={'csrf_token': FakeCsrf.valid_token})

        data_api_client.update_user.assert_called_with(999, locked=False, updater="test@example.com")

        self.assertEquals(302, response.status_code)
        self.assertEquals('http://localhost/admin/suppliers/users?supplier_code=1000', response.location)

    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_call_api_to_activate_user(self, data_api_client):
        data_api_client.get_supplier.return_value = self.load_example_listing("supplier_response")
        data_api_client.update_user.return_value = self.load_example_listing("user_response")

        response = self.client.post('/admin/suppliers/users/999/activate', data={'csrf_token': FakeCsrf.valid_token})

        data_api_client.update_user.assert_called_with(999, active=True, updater="test@example.com")

        self.assertEquals(302, response.status_code)
        self.assertEquals('http://localhost/admin/suppliers/users?supplier_code=1000', response.location)

    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_call_api_to_deactivate_user(self, data_api_client):
        data_api_client.get_supplier.return_value = self.load_example_listing("supplier_response")
        data_api_client.update_user.return_value = self.load_example_listing("user_response")

        response = self.client.post(
            '/admin/suppliers/users/999/deactivate',
            data={
                'supplier_code': 1000,
                'csrf_token': FakeCsrf.valid_token,
            }
        )

        data_api_client.update_user.assert_called_with(999, active=False, updater="test@example.com")

        self.assertEquals(302, response.status_code)
        self.assertEquals('http://localhost/admin/suppliers/users?supplier_code=1000', response.location)

    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_call_api_to_move_user_to_another_supplier(self, data_api_client):
        data_api_client.get_supplier.return_value = self.load_example_listing("supplier_response")
        data_api_client.get_user.return_value = self.load_example_listing("user_response")
        data_api_client.update_user.return_value = self.load_example_listing("user_response")

        response = self.client.post(
            '/admin/suppliers/1000/move-existing-user',
            data={
                'user_to_move_email_address': 'test.user@sme.com',
                'csrf_token': FakeCsrf.valid_token,
            }
        )

        data_api_client.update_user.assert_called_with(
            999, role='supplier', supplier_code=1000, active=True, updater='test@example.com'
        )

        self.assertEquals(302, response.status_code)
        self.assertEquals('http://localhost/admin/suppliers/users?supplier_code=1000', response.location)


class TestSupplierServicesView(LoggedInApplicationTest):

    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_404_if_supplier_does_not_exist_on_services(self, data_api_client):
        data_api_client.get_supplier.side_effect = HTTPError(Response(404))
        response = self.client.get('/admin/suppliers/services?supplier_code=999')
        self.assertEquals(404, response.status_code)

    def test_should_404_if_no_supplier_code_on_services(self):
        response = self.client.get('/admin/suppliers/users')
        self.assertEquals(404, response.status_code)

    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_call_service_apis_with_supplier_code(self, data_api_client):
        data_api_client.get_supplier.return_value = self.load_example_listing("supplier_response")
        response = self.client.get('/admin/suppliers/services?supplier_code=1000')

        self.assertEquals(200, response.status_code)

        data_api_client.get_supplier.assert_called_with(1000)
        data_api_client.find_services.assert_called_with(1000)

    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_indicate_if_supplier_has_no_services(self, data_api_client):
        data_api_client.get_supplier.return_value = self.load_example_listing("supplier_response_with_no_services")
        data_api_client.find_services.return_value = {'services': []}
        response = self.client.get('/admin/suppliers/services?supplier_code=1000')

        self.assertEquals(200, response.status_code)
        self.assertIn(
            "This supplier has no services on the Digital Marketplace",
            response.get_data(as_text=True)
        )
        self.assertIn(
            "This supplier has no services to assess",
            response.get_data(as_text=True)
        )

    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_have_supplier_name_on_services_page(self, data_api_client):
        data_api_client.get_supplier.return_value = self.load_example_listing("supplier_response")
        data_api_client.find_services.return_value = {'services': []}

        response = self.client.get('/admin/suppliers/services?supplier_code=1000')

        self.assertEquals(200, response.status_code)
        self.assertIn(
            'Example Pty Ltd',
            response.get_data(as_text=True)
        )

    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_show_services_to_assess(self, data_api_client):
        data_api_client.get_supplier.return_value = self.load_example_listing("supplier_response")

        response = self.client.get('/admin/suppliers/services?supplier_code=1000')

        self.assertEquals(200, response.status_code)
        self.assertIn(
            "Cyber security",
            response.get_data(as_text=True)
        )

    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_show_assessed_services(self, data_api_client):
        data_api_client.get_supplier.return_value = self.load_example_listing("supplier_response")

        response = self.client.get('/admin/suppliers/services?supplier_code=1000')

        self.assertEquals(200, response.status_code)
        self.assertIn(
            "Data science",
            response.get_data(as_text=True)
        )


class TestSupplierInviteUserView(LoggedInApplicationTest):

    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_not_acccept_bad_email_on_invite_user(self, data_api_client):
        data_api_client.get_supplier.return_value = self.load_example_listing("supplier_response")
        data_api_client.find_users.return_value = self.load_example_listing("users_response")

        response = self.client.post(
            '/admin/suppliers/1234/invite-user',
            data={
                'name': 'A Name',
                'email_address': 'notatallvalid',
                'csrf_token': FakeCsrf.valid_token,
            },
            follow_redirects=True
        )

        self.assertEquals(400, response.status_code)
        self.assertTrue("Please enter a valid email address" in response.get_data(as_text=True))

    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_not_allow_missing_name_on_invite_user(self, data_api_client):
        data_api_client.get_supplier.return_value = self.load_example_listing("supplier_response")
        data_api_client.find_users.return_value = self.load_example_listing("users_response")

        response = self.client.post(
            '/admin/suppliers/1234/invite-user',
            data={
                'email_address': 'test@example.com',
                'csrf_token': FakeCsrf.valid_token,
            },
            follow_redirects=True
        )

        self.assertEquals(400, response.status_code)
        self.assertTrue('name' in response.get_data(as_text=True))

    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_not_allow_missing_email_on_invite_user(self, data_api_client):
        data_api_client.get_supplier.return_value = self.load_example_listing("supplier_response")
        data_api_client.find_users.return_value = self.load_example_listing("users_response")

        response = self.client.post(
            '/admin/suppliers/1234/invite-user',
            data={
                'name': 'A Name',
                'csrf_token': FakeCsrf.valid_token,
            },
            follow_redirects=True
        )

        self.assertEquals(400, response.status_code)
        self.assertTrue("Email cannot be empty" in response.get_data(as_text=True))

    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_be_a_404_if_non_int_supplier_code(self, data_api_client):

        response = self.client.post(
            '/admin/suppliers/bad/invite-user',
            data={'csrf_token': FakeCsrf.valid_token},
            follow_redirects=True
        )

        self.assertEquals(404, response.status_code)
        self.assertFalse(data_api_client.called)

    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_be_a_404_if_supplier_code_not_found(self, data_api_client):

        data_api_client.get_supplier.side_effect = HTTPError(Response(404))

        response = self.client.post(
            '/admin/suppliers/1234/invite-user',
            data={'csrf_token': FakeCsrf.valid_token},
            follow_redirects=True
        )

        data_api_client.get_supplier.assert_called_with(1234)
        self.assertFalse(data_api_client.find_users.called)
        self.assertEquals(404, response.status_code)

    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_be_a_404_if_supplier_users_not_found(self, data_api_client):
        data_api_client.get_supplier.return_value = self.load_example_listing("supplier_response")
        data_api_client.find_users.side_effect = HTTPError(Response(404))

        response = self.client.post(
            '/admin/suppliers/1234/invite-user',
            data={'csrf_token': FakeCsrf.valid_token},
            follow_redirects=True
        )

        data_api_client.get_supplier.assert_called_with(1234)
        data_api_client.find_users.assert_called_with(1234)
        self.assertEquals(404, response.status_code)

    @mock.patch('app.main.views.suppliers.generate_token')
    @mock.patch('app.main.views.suppliers.send_email')
    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_call_generate_token_with_correct_params(self, data_api_client, send_email, generate_token):
        data_api_client.get_supplier.return_value = self.load_example_listing("supplier_response")
        data_api_client.find_users.return_value = self.load_example_listing("users_response")
        send_email.return_value = True

        res = self.client.post(
            '/admin/suppliers/1234/invite-user',
            data={
                'name': 'A Name',
                'email_address': 'this@isvalid.com',
                'csrf_token': FakeCsrf.valid_token,
            })

        generate_token.assert_called_once_with(
            {
                'supplierCode': 1234,
                'supplierName': 'Example Pty Ltd',
                'emailAddress': 'this@isvalid.com',
                'name': 'A Name',
            },
            self.app.config['SECRET_KEY'],
            self.app.config['INVITE_EMAIL_SALT'],
        )

        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.location, 'http://localhost/admin/suppliers/users?supplier_code=1234')

    @mock.patch('app.main.views.suppliers.send_email')
    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_call_send_email_with_correct_params(self, data_api_client, send_email):
        data_api_client.get_supplier.return_value = self.load_example_listing("supplier_response")
        data_api_client.find_users.return_value = self.load_example_listing("users_response")

        res = self.client.post(
            '/admin/suppliers/1234/invite-user',
            data={
                'name': 'A Name',
                'email_address': 'this@isvalid.com',
                'csrf_token': FakeCsrf.valid_token,
            }
        )

        send_email.assert_called_once_with(
            'this@isvalid.com',
            mock.ANY,
            'Your Digital Marketplace invitation',
            self.app.config['INVITE_EMAIL_FROM'],
            self.app.config['INVITE_EMAIL_NAME'],
        )

        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.location, 'http://localhost/admin/suppliers/users?supplier_code=1234')

    @mock.patch('app.main.views.suppliers.send_email')
    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_strip_whitespace_surrounding_invite_user_email_address_field(self, data_api_client, send_email):
        data_api_client.get_supplier.return_value = self.load_example_listing("supplier_response")
        data_api_client.find_users.return_value = self.load_example_listing("users_response")

        res = self.client.post(
            '/admin/suppliers/1234/invite-user',
            data={
                'name': 'A Name',
                'email_address': '  this@isvalid.com  ',
                'csrf_token': FakeCsrf.valid_token,
            }
        )
        assert res.status_code < 400

        send_email.assert_called_once_with(
            'this@isvalid.com',
            mock.ANY,
            mock.ANY,
            mock.ANY,
            mock.ANY,
        )

    @mock.patch('app.main.views.suppliers.generate_token')
    @mock.patch('app.main.views.suppliers.render_template')
    @mock.patch('app.main.views.suppliers.send_email')
    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_call_render_template_with_correct_params(self, data_api_client,
                                                             send_email, render_template, generate_token):
        data_api_client.get_supplier.return_value = self.load_example_listing("supplier_response")
        data_api_client.find_users.return_value = self.load_example_listing("users_response")
        send_email.return_value = True
        generate_token.return_value = "token"

        res = self.client.post(
            '/admin/suppliers/1234/invite-user',
            data={
                'name': 'A Name',
                'email_address': 'this@isvalid.com',
                'csrf_token': FakeCsrf.valid_token,
            }
        )
        render_template.assert_called_once_with(
            'emails/invite_user_email.html',
            url='http://localhost/sellers/create-user/token',
            supplier='Example Pty Ltd',
            name='A Name',
        )

        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.location, 'http://localhost/admin/suppliers/users?supplier_code=1234')

    @mock.patch('app.main.views.suppliers.send_email')
    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_be_a_503_if_email_fails(self, data_api_client, send_email):
        data_api_client.get_supplier.return_value = self.load_example_listing("supplier_response")
        data_api_client.find_users.return_value = self.load_example_listing("users_response")
        send_email.side_effect = EmailError("Arrrgh")
        res = self.client.post(
            "/admin/suppliers/1234/invite-user",
            data={
                'name': 'A Name',
                'email_address': 'this@isvalid.com',
                'csrf_token': FakeCsrf.valid_token,
            })

        send_email.assert_called_once_with(
            u'this@isvalid.com',
            mock.ANY,
            'Your Digital Marketplace invitation',
            self.app.config['INVITE_EMAIL_FROM'],
            self.app.config['INVITE_EMAIL_NAME'],
        )

        self.assertEqual(res.status_code, 503)


@mock.patch('app.main.views.suppliers.data_api_client')
class TestViewingASupplierDeclaration(LoggedInApplicationTest):
    user_role = 'admin-ccs-sourcing'

    def test_should_not_be_visible_to_admin_users(self, data_api_client):
        self.user_role = 'admin'

        response = self.client.get('/admin/suppliers/1234/edit/declarations/g-cloud-7')

        eq_(response.status_code, 403)

    def test_should_404_if_supplier_does_not_exist(self, data_api_client):
        data_api_client.get_supplier.side_effect = APIError(Response(404))

        response = self.client.get('/admin/suppliers/1234/edit/declarations/g-cloud-7')

        eq_(response.status_code, 404)
        data_api_client.get_supplier.assert_called_with('1234')
        assert not data_api_client.get_framework.called

    def test_should_404_if_framework_does_not_exist(self, data_api_client):
        data_api_client.get_supplier.return_value = self.load_example_listing('supplier_response')
        data_api_client.get_framework.side_effect = APIError(Response(404))

        response = self.client.get('/admin/suppliers/1234/edit/declarations/g-cloud-7')

        eq_(response.status_code, 404)
        data_api_client.get_supplier.assert_called_with('1234')
        data_api_client.get_framework.assert_called_with('g-cloud-7')

    def test_should_not_404_if_declaration_does_not_exist(self, data_api_client):
        data_api_client.get_supplier.return_value = self.load_example_listing('supplier_response')
        data_api_client.get_framework.return_value = self.load_example_listing('framework_response')
        data_api_client.get_supplier_declaration.side_effect = APIError(Response(404))

        response = self.client.get('/admin/suppliers/1234/edit/declarations/g-cloud-7')

        eq_(response.status_code, 200)
        data_api_client.get_supplier.assert_called_with('1234')
        data_api_client.get_framework.assert_called_with('g-cloud-7')
        data_api_client.get_supplier_declaration.assert_called_with('1234', 'g-cloud-7')

    def test_should_show_declaration(self, data_api_client):
        data_api_client.get_supplier.return_value = self.load_example_listing('supplier_response')
        data_api_client.get_framework.return_value = self.load_example_listing('framework_response')
        data_api_client.get_supplier_declaration.return_value = self.load_example_listing('declaration_response')

        response = self.client.get('/admin/suppliers/1234/edit/declarations/g-cloud-7')
        document = html.fromstring(response.get_data(as_text=True))

        eq_(response.status_code, 200)
        data = document.cssselect('.summary-item-row td.summary-item-field')
        eq_(data[0].text_content().strip(), "Yes")

    def test_should_show_dos_declaration(self, data_api_client):
        data_api_client.get_supplier.return_value = self.load_example_listing('supplier_response')
        data_api_client.get_framework.return_value = self.load_example_listing('framework_response')
        data_api_client.get_supplier_declaration.return_value = self.load_example_listing('declaration_response')

        response = self.client.get('/admin/suppliers/1234/edit/declarations/digital-outcomes-and-specialists')
        document = html.fromstring(response.get_data(as_text=True))

        eq_(response.status_code, 200)
        data = document.cssselect('.summary-item-row td.summary-item-field')
        eq_(data[0].text_content().strip(), "Yes")

    def test_should_403_if_framework_is_open(self, data_api_client):
        data_api_client.get_supplier.return_value = self.load_example_listing('supplier_response')
        data_api_client.get_framework.return_value = self.load_example_listing('framework_response')
        data_api_client.get_framework.return_value['frameworks']['status'] = 'open'
        data_api_client.get_supplier_declaration.return_value = self.load_example_listing('declaration_response')

        response = self.client.get('/admin/suppliers/1234/edit/declarations/digital-outcomes-and-specialists')
        eq_(response.status_code, 403)


@mock.patch('app.main.views.suppliers.data_api_client')
class TestEditingASupplierDeclaration(LoggedInApplicationTest):
    user_role = 'admin-ccs-sourcing'

    def test_should_not_be_visible_to_admin_users(self, data_api_client):
        self.user_role = 'admin'

        response = self.client.get('/admin/suppliers/1234/edit/declarations/g-cloud-7/section')

        eq_(response.status_code, 403)

    def test_should_404_if_supplier_does_not_exist(self, data_api_client):
        data_api_client.get_supplier.side_effect = APIError(Response(404))

        response = self.client.get('/admin/suppliers/1234/edit/declarations/g-cloud-7/g-cloud-7-essentials')

        eq_(response.status_code, 404)
        data_api_client.get_supplier.assert_called_with('1234')
        assert not data_api_client.get_framework.called

    def test_should_404_if_framework_does_not_exist(self, data_api_client):
        data_api_client.get_supplier.return_value = self.load_example_listing('supplier_response')
        data_api_client.get_framework.side_effect = APIError(Response(404))

        response = self.client.get('/admin/suppliers/1234/edit/declarations/g-cloud-7/g-cloud-7-essentials')

        eq_(response.status_code, 404)
        data_api_client.get_supplier.assert_called_with('1234')
        data_api_client.get_framework.assert_called_with('g-cloud-7')

    def test_should_404_if_section_does_not_exist(self, data_api_client):
        data_api_client.get_supplier.return_value = self.load_example_listing('supplier_response')
        data_api_client.get_framework.return_value = self.load_example_listing('framework_response')
        data_api_client.get_supplier_declaration.side_effect = APIError(Response(404))

        response = self.client.get('/admin/suppliers/1234/edit/declarations/g-cloud-7/not_a_section')

        eq_(response.status_code, 404)

    def test_should_not_404_if_declaration_does_not_exist(self, data_api_client):
        data_api_client.get_supplier.return_value = self.load_example_listing('supplier_response')
        data_api_client.get_framework.return_value = self.load_example_listing('framework_response')
        data_api_client.get_supplier_declaration.side_effect = APIError(Response(404))

        response = self.client.get('/admin/suppliers/1234/edit/declarations/g-cloud-7/g-cloud-7-essentials')

        eq_(response.status_code, 200)
        data_api_client.get_supplier.assert_called_with('1234')
        data_api_client.get_framework.assert_called_with('g-cloud-7')
        data_api_client.get_supplier_declaration.assert_called_with('1234', 'g-cloud-7')

    def test_should_prefill_form_with_declaration(self, data_api_client):
        data_api_client.get_supplier.return_value = self.load_example_listing('supplier_response')
        data_api_client.get_framework.return_value = self.load_example_listing('framework_response')
        data_api_client.get_supplier_declaration.return_value = self.load_example_listing('declaration_response')

        response = self.client.get('/admin/suppliers/1234/edit/declarations/g-cloud-7/g-cloud-7-essentials')
        document = html.fromstring(response.get_data(as_text=True))

        eq_(response.status_code, 200)
        assert document.cssselect('#input-PR1-yes')[0].checked
        assert not document.cssselect('#input-PR1-no')[0].checked

    def test_should_set_declaration(self, data_api_client):
        data_api_client.get_supplier.return_value = self.load_example_listing('supplier_response')
        data_api_client.get_framework.return_value = self.load_example_listing('framework_response')
        data_api_client.get_supplier_declaration.return_value = self.load_example_listing('declaration_response')

        response = self.client.post(
            '/admin/suppliers/1234/edit/declarations/g-cloud-7/g-cloud-7-essentials',
            data={
                'PR1': 'false',
                'csrf_token': FakeCsrf.valid_token,
            }
        )

        assert response.status_code == 302

        declaration = self.load_example_listing('declaration_response')['declaration']
        declaration['PR1'] = False
        declaration['SQ1-3'] = None
        declaration['SQC3'] = None

        data_api_client.set_supplier_declaration.assert_called_with(
            '1234', 'g-cloud-7', declaration, 'test@example.com')


@mock.patch('app.main.views.suppliers.data_api_client')
@mock.patch('app.main.views.suppliers.s3')
class TestDownloadAgreementFile(LoggedInApplicationTest):
    user_role = 'admin-ccs-sourcing'

    def test_category_admin_user_should_not_be_able_to_download(self, s3, data_api_client):
        self.user_role = 'admin-ccs-category'

        response = self.client.get('/admin/suppliers/1234/agreements/g-cloud-7/foo.pdf')

        eq_(response.status_code, 403)

    def test_should_404_if_no_documents_listed(self, s3, data_api_client):
        data_api_client.get_supplier_framework_info.return_value = {
            'frameworkInterest': {'declaration': {'SQ1-1a': 'Supplier name'}}
        }
        s3.S3.return_value.list.return_value = []
        response = self.client.get('/admin/suppliers/1234/agreements/g-cloud-7/foo')

        assert not s3.S3.return_value.get_signed_url.called
        eq_(response.status_code, 404)

    @pytest.mark.skip
    def test_should_404_if_document_does_not_exist(self, s3, data_api_client):
        data_api_client.get_supplier_framework_info.return_value = {
            'frameworkInterest': {'declaration': {'SQ1-1a': 'Supplier name'}}
        }
        s3.S3.return_value.list.return_value = [
            {'path': 'g-cloud-7/agreements/1234/1234-foo.pdf'}
        ]
        s3.S3.return_value.get_signed_url.return_value = None

        response = self.client.get('/admin/suppliers/1234/agreements/g-cloud-7/foo')

        s3.S3.return_value.list.assert_called_with(prefix='g-cloud-7/agreements/1234/1234-foo')
        s3.S3.return_value.get_signed_url.assert_called_with('g-cloud-7/agreements/1234/1234-foo.pdf')
        eq_(response.status_code, 404)

    @pytest.mark.skip
    def test_should_select_most_recent_matching_file(self, s3, data_api_client):
        data_api_client.get_supplier_framework_info.return_value = {
            'frameworkInterest': {'declaration': {'key': 'value'}}
        }
        s3.S3.return_value.list.return_value = [
            {'path': 'foo.jpg'},
            {'path': 'g-cloud-7/agreements/1234/1234-foo.pdf'}
        ]
        s3.S3.return_value.get_signed_url.return_value = 'http://foo/blah?extra'

        self.app.config['DM_ASSETS_URL'] = 'https://example'

        self.client.get('/admin/suppliers/1234/agreements/g-cloud-7/foo')

        s3.S3.return_value.list.assert_called_with(prefix='g-cloud-7/agreements/1234/1234-foo')
        s3.S3.return_value.get_signed_url.assert_called_with('g-cloud-7/agreements/1234/1234-foo.pdf')

    @pytest.mark.skip
    def test_should_redirect(self, s3, data_api_client):
        data_api_client.get_supplier_framework_info.return_value = {
            'frameworkInterest': {'declaration': {'key': 'Supplier name'}}
        }
        s3.S3.return_value.list.return_value = [
            {'path': 'g-cloud-7/agreements/1234/1234-foo.pdf'}
        ]
        s3.S3.return_value.get_signed_url.return_value = 'http://foo/blah?extra'

        self.app.config['DM_ASSETS_URL'] = 'https://example'

        response = self.client.get('/admin/suppliers/1234/agreements/g-cloud-7/foo')

        eq_(response.status_code, 302)
        eq_(response.location, 'https://example/blah?extra')

        s3.S3.return_value.list.assert_called_with(prefix='g-cloud-7/agreements/1234/1234-foo')
        s3.S3.return_value.get_signed_url.assert_called_with('g-cloud-7/agreements/1234/1234-foo.pdf')

    @pytest.mark.skip
    def test_admin_should_be_able_to_download_countersigned_agreement(self, s3, data_api_client):
        data_api_client.get_supplier_framework_info.return_value = {
            'frameworkInterest': {'declaration': {'key': 'value'}}
        }
        s3.S3.return_value.list.return_value = [
            {'path': 'g-cloud-7/agreements/1234/1234-countersigned-framework-agreement.pdf'}
        ]
        s3.S3.return_value.get_signed_url.return_value = 'http://foo/blah?extra'

        self.app.config['DM_ASSETS_URL'] = 'https://example'

        response = self.client.get(
            '/admin/suppliers/1234/agreements/g-cloud-7/countersigned-framework-agreement.pdf'
        )

        s3.S3.return_value.list.assert_called_with(
            prefix='g-cloud-7/agreements/1234/1234-countersigned-framework-agreement.pdf'
        )
        s3.S3.return_value.get_signed_url.assert_called_with(
            'g-cloud-7/agreements/1234/1234-countersigned-framework-agreement.pdf'
        )
        eq_(response.status_code, 302)


@mock.patch('app.main.views.suppliers.data_api_client')
@mock.patch('app.main.views.suppliers.s3')
class TestListCountersignedAgreementFile(LoggedInApplicationTest):
    user_role = 'admin-ccs-sourcing'

    def test_should_not_be_visible_to_admin_users(self, s3, data_api_client):
        self.user_role = 'admin'

        response = self.client.get('/admin/suppliers/1234/countersigned-agreements/g-cloud-7')

        eq_(response.status_code, 403)

    def test_should_be_visible_to_admin_sourcing_users(self, s3, data_api_client):
        s3.S3.return_value.get_key.return_value = {
            'size': '7050',
            'path': u'g-cloud-7/agreements/93495/93495-countersigned-framework-agreement.pdf',
            'ext': u'pdf',
            'last_modified': u'2016-01-15T12:58:08.000000Z',
            'filename': u'93495-countersigned-framework-agreement'
        }
        response = self.client.get('/admin/suppliers/1234/countersigned-agreements/g-cloud-7')
        eq_(response.status_code, 200)

    def test_should_display_no_documents_if_no_documents_listed(self, s3, data_api_client):
        s3.S3.return_value.get_key.return_value = []
        response = self.client.get('/admin/suppliers/1234/countersigned-agreements/g-cloud-7')
        self.assertIn(
            'No agreements have been uploaded',
            response.get_data(as_text=True)
        )


@mock.patch('app.main.views.suppliers.data_api_client')
@mock.patch('app.main.views.suppliers.s3')
class TestUploadCountersignedAgreementFile(LoggedInApplicationTest):
    user_role = 'admin-ccs-sourcing'

    def test_countersigned_agreement_displays_error_for_wrong_format(self, s3, data_api_client):
        s3.S3.return_value.get_key.return_value = {
            'size': '7050',
            'path': u'g-cloud-7/agreements/93495/93495-countersigned-framework-agreement.pdf',
            'ext': u'pdf',
            'last_modified': u'2016-01-15T12:58:08.000000Z',
            'filename': u'93495-countersigned-framework-agreement'
        }
        response = self.client.post(
            '/admin/suppliers/1234/countersigned-agreements/g-cloud-7',
            data={
                'countersigned_agreement': (io.BytesIO(b"this is a test"), 'test.odt'),
                'csrf_token': FakeCsrf.valid_token,
            },
            follow_redirects=True
        )

        self.assertIn(
            'This must be a pdf',
            response.get_data(as_text=True)
        )
        eq_(response.status_code, 200)

    def test_should_create_audit_event(self, s3, data_api_client):
        s3.S3.return_value.get_key.return_value = {
            'size': '7050',
            'path': u'g-cloud-7/agreements/1234/1234-countersigned-framework-agreement.pdf',
            'ext': u'pdf',
            'last_modified': u'2016-01-15T12:58:08.000000Z',
            'filename': u'1234-countersigned-framework-agreement'
        }

        response = self.client.post(
            '/admin/suppliers/1234/countersigned-agreements/g-cloud-7',
            data={
                'countersigned_agreement': (io.BytesIO(b"this is a test"), 'countersigned_agreement.pdf'),
                'csrf_token': FakeCsrf.valid_token,
            },
            follow_redirects=True
        )

        data_api_client.create_audit_event.assert_called_once_with(
            audit_type=AuditTypes.upload_countersigned_agreement,
            user='test@example.com',
            object_type='suppliers',
            object_id=u'1234',
            data={'upload_countersigned_agreement': 'g-cloud-7/agreements/1234/1234-countersigned-'
                  'framework-agreement.pdf'})

        self.assertIn(
            'Countersigned agreement file was uploaded',
            response.get_data(as_text=True)
        )
        self.assertEqual(response.status_code, 200)


@mock.patch('app.main.views.suppliers.data_api_client')
@mock.patch('app.main.views.suppliers.s3')
class TestRemoveCountersignedAgreementFile(LoggedInApplicationTest):
    user_role = 'admin-ccs-sourcing'

    def test_should_remove_countersigned_agreement(self, s3, data_api_client):
        s3.S3.return_value.delete_key.return_value = {'Key': 'digitalmarketplace-documents-dev-dev'
                                                      ',g-cloud-7/agreements/93495/93495-'
                                                      'countersigned-framework-agreement.pdf'}
        response = self.client.post(
            '/admin/suppliers/1234/countersigned-agreements-remove/g-cloud-7',
            data={'csrf_token': FakeCsrf.valid_token},
        )
        eq_(response.status_code, 302)

    def test_admin_should_not_be_able_to_remove_countersigned_agreement(self, s3, data_api_client):
        self.user_role = 'admin'
        s3.S3.return_value.delete_key.return_value = {'Key': 'digitalmarketplace-documents-dev-dev'
                                                      ',g-cloud-7/agreements/93495/93495-'
                                                      'countersigned-framework-agreement.pdf'}
        response = self.client.post(
            '/admin/suppliers/1234/countersigned-agreements-remove/g-cloud-7',
            data={'csrf_token': FakeCsrf.valid_token},
        )
        eq_(response.status_code, 403)

    def test_should_display_remove_countersigned_agreement_message(self, s3, data_api_client):
        s3.S3.return_value.get_key.return_value = {
            'size': '7050',
            'path': u'g-cloud-7/agreements/93495/93495-countersigned-framework-agreement.pdf',
            'ext': u'pdf',
            'last_modified': u'2016-01-15T12:58:08.000000Z',
            'filename': u'93495-countersigned-framework-agreement'
        }
        response = self.client.get('/admin/suppliers/1234/countersigned-agreements-remove/g-cloud-7',
                                   follow_redirects=True)
        self.assertIn(
            'Do you want to remove the countersigned agreement?',
            response.get_data(as_text=True)
        )
        eq_(response.status_code, 200)
