from six import BytesIO
from six.moves.urllib.parse import urlsplit, urlparse, parse_qs
import mock
from freezegun import freeze_time
from lxml import html
from nose.tools import eq_
from nose.tools import assert_equals
from dmapiclient import HTTPError, APIError
from dmutils.email import MandrillException
from dmapiclient.audit import AuditTypes
from ...helpers import LoggedInApplicationTest, Response
from ..helpers.flash_tester import assert_flashes


@mock.patch('app.main.views.suppliers.data_api_client')
class TestSuppliersListView(LoggedInApplicationTest):

    def test_should_raise_http_error_from_api(self, data_api_client):
        data_api_client.find_suppliers.side_effect = HTTPError(Response(404))
        response = self.client.get('/admin/suppliers')
        assert_equals(response.status_code, 404)

    def test_should_list_suppliers(self, data_api_client):
        data_api_client.find_suppliers.return_value = {
            "suppliers": [
                {"id": 1234, "name": "Supplier 1"},
                {"id": 1235, "name": "Supplier 2"},
            ]
        }
        data_api_client.get_supplier_framework_info.side_effect = [
            {"frameworkInterest": {"agreementPath": "path/the/first/1234-g7-agreement.pdf"}},
            {"frameworkInterest": {"agreementPath": None}},  # Supplier 1234 hasn't returned their DOS agreement yet
            HTTPError(Response(404)),                        # Supplier 1235 isn't on G-Cloud 7
            {"frameworkInterest": {"agreementPath": "path/the/third/1235-dos-agreement.jpg"}},
        ]
        response = self.client.get("/admin/suppliers")
        document = html.fromstring(response.get_data(as_text=True))

        assert_equals(response.status_code, 200)
        assert_equals(len(document.cssselect('.summary-item-row')), 2)

    def test_should_search_by_prefix(self, data_api_client):
        data_api_client.find_suppliers.side_effect = HTTPError(Response(404))
        self.client.get("/admin/suppliers?supplier_name_prefix=foo")

        data_api_client.find_suppliers.assert_called_once_with(prefix="foo", duns_number=None)

    def test_should_search_by_duns_number(self, data_api_client):
        data_api_client.find_suppliers.side_effect = HTTPError(Response(404))
        self.client.get("/admin/suppliers?supplier_duns_number=987654321")

        data_api_client.find_suppliers.assert_called_once_with(prefix=None, duns_number="987654321")

    def test_should_find_by_supplier_id(self, data_api_client):
        data_api_client.get_supplier.side_effect = HTTPError(Response(404))
        self.client.get("/admin/suppliers?supplier_id=12345")

        data_api_client.get_supplier.assert_called_once_with("12345")


class TestSupplierUsersView(LoggedInApplicationTest):

    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_404_if_no_supplier_does_not_exist(self, data_api_client):
        data_api_client.get_supplier.side_effect = HTTPError(Response(404))
        response = self.client.get('/admin/suppliers/users?supplier_id=999')
        self.assertEquals(404, response.status_code)

    def test_should_404_if_no_supplier_id(self):
        response = self.client.get('/admin/suppliers/users')
        self.assertEquals(404, response.status_code)

    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_call_apis_with_supplier_id(self, data_api_client):
        data_api_client.get_supplier.return_value = self.load_example_listing("supplier_response")
        response = self.client.get('/admin/suppliers/users?supplier_id=1000')

        self.assertEquals(200, response.status_code)

        data_api_client.get_supplier.assert_called_with('1000')
        data_api_client.find_users.assert_called_with('1000')

    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_have_supplier_name_on_page(self, data_api_client):
        data_api_client.get_supplier.return_value = self.load_example_listing("supplier_response")
        response = self.client.get('/admin/suppliers/users?supplier_id=1000')

        self.assertEquals(200, response.status_code)
        self.assertIn(
            "Supplier Name",
            response.get_data(as_text=True)
        )

    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_indicate_if_there_are_no_users(self, data_api_client):
        data_api_client.get_supplier.return_value = self.load_example_listing("supplier_response")
        data_api_client.find_users.return_value = {'users': {}}

        response = self.client.get('/admin/suppliers/users?supplier_id=1000')

        self.assertEquals(200, response.status_code)
        self.assertIn(
            "This supplier has no users on the Digital Marketplace",
            response.get_data(as_text=True)
        )

    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_show_user_details_on_page(self, data_api_client):
        data_api_client.get_supplier.return_value = self.load_example_listing("supplier_response")
        data_api_client.find_users.return_value = self.load_example_listing("users_response")

        response = self.client.get('/admin/suppliers/users?supplier_id=1000')

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
            "10:33:53",
            response.get_data(as_text=True)
        )
        self.assertIn(
            "23 July",
            response.get_data(as_text=True)
        )
        self.assertIn(
            "13:46:01",
            response.get_data(as_text=True)
        )
        self.assertIn(
            "29 June",
            response.get_data(as_text=True)
        )
        self.assertIn(
            "No",
            response.get_data(as_text=True)
        )

        self.assertIn(
            '<input type="submit" class="button-destructive"  value="Deactivate" />',
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
            '<form action="/admin/suppliers/1234/move-existing-user" method="post">',
            response.get_data(as_text=True)
        )

    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_show_unlock_button_if_user_locked(self, data_api_client):
        data_api_client.get_supplier.return_value = self.load_example_listing("supplier_response")

        users = self.load_example_listing("users_response")
        users["users"][0]["locked"] = True
        data_api_client.find_users.return_value = users

        response = self.client.get('/admin/suppliers/users?supplier_id=1000')

        self.assertEquals(200, response.status_code)
        self.assertIn(
            '<form action="/admin/suppliers/users/999/unlock" method="post">',
            response.get_data(as_text=True)
        )
        self.assertIn(
            '<input type="submit" class="button-secondary"  value="Unlock" />',
            response.get_data(as_text=True)
        )

    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_show_activate_button_if_user_deactivated(self, data_api_client):
        data_api_client.get_supplier.return_value = self.load_example_listing("supplier_response")

        users = self.load_example_listing("users_response")
        users["users"][0]["active"] = False
        data_api_client.find_users.return_value = users

        response = self.client.get('/admin/suppliers/users?supplier_id=1000')

        self.assertEquals(200, response.status_code)
        self.assertIn(
            '<form action="/admin/suppliers/users/999/activate" method="post">',
            response.get_data(as_text=True)
        )
        self.assertIn(
            '<input type="submit" class="button-secondary"  value="Activate" />',
            response.get_data(as_text=True)
        )

    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_call_api_to_unlock_user(self, data_api_client):
        data_api_client.get_supplier.return_value = self.load_example_listing("supplier_response")
        data_api_client.update_user.return_value = self.load_example_listing("user_response")

        response = self.client.post('/admin/suppliers/users/999/unlock')

        data_api_client.update_user.assert_called_with(999, locked=False, updater="test@example.com")

        self.assertEquals(302, response.status_code)
        self.assertEquals("http://localhost/admin/suppliers/users?supplier_id=1000", response.location)

    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_call_api_to_activate_user(self, data_api_client):
        data_api_client.get_supplier.return_value = self.load_example_listing("supplier_response")
        data_api_client.update_user.return_value = self.load_example_listing("user_response")

        response = self.client.post('/admin/suppliers/users/999/activate')

        data_api_client.update_user.assert_called_with(999, active=True, updater="test@example.com")

        self.assertEquals(302, response.status_code)
        self.assertEquals("http://localhost/admin/suppliers/users?supplier_id=1000", response.location)

    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_call_api_to_deactivate_user(self, data_api_client):
        data_api_client.get_supplier.return_value = self.load_example_listing("supplier_response")
        data_api_client.update_user.return_value = self.load_example_listing("user_response")

        response = self.client.post(
            '/admin/suppliers/users/999/deactivate',
            data={'supplier_id': 1000}
        )

        data_api_client.update_user.assert_called_with(999, active=False, updater="test@example.com")

        self.assertEquals(302, response.status_code)
        self.assertEquals("http://localhost/admin/suppliers/users?supplier_id=1000", response.location)

    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_call_api_to_move_user_to_another_supplier(self, data_api_client):
        data_api_client.get_supplier.return_value = self.load_example_listing("supplier_response")
        data_api_client.get_user.return_value = self.load_example_listing("user_response")
        data_api_client.update_user.return_value = self.load_example_listing("user_response")

        response = self.client.post(
            '/admin/suppliers/1000/move-existing-user',
            data={'user_to_move_email_address': 'test.user@sme.com'}
        )

        data_api_client.update_user.assert_called_with(
            999, role='supplier', supplier_id=1000, active=True, updater="test@example.com"
        )

        self.assertEquals(302, response.status_code)
        self.assertEquals("http://localhost/admin/suppliers/users?supplier_id=1000", response.location)


class TestSupplierServicesView(LoggedInApplicationTest):

    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_404_if_supplier_does_not_exist_on_services(self, data_api_client):
        data_api_client.get_supplier.side_effect = HTTPError(Response(404))
        response = self.client.get('/admin/suppliers/services?supplier_id=999')
        self.assertEquals(404, response.status_code)

    def test_should_404_if_no_supplier_id_on_services(self):
        response = self.client.get('/admin/suppliers/users')
        self.assertEquals(404, response.status_code)

    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_call_service_apis_with_supplier_id(self, data_api_client):
        data_api_client.get_supplier.return_value = self.load_example_listing("supplier_response")
        response = self.client.get('/admin/suppliers/services?supplier_id=1000')

        self.assertEquals(200, response.status_code)

        data_api_client.get_supplier.assert_called_with('1000')
        data_api_client.find_services.assert_called_with('1000')

    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_indicate_if_supplier_has_no_services(self, data_api_client):
        data_api_client.get_supplier.return_value = self.load_example_listing("supplier_response")
        data_api_client.find_services.return_value = {'services': []}
        response = self.client.get('/admin/suppliers/services?supplier_id=1000')

        self.assertEquals(200, response.status_code)
        self.assertIn(
            "This supplier has no services on the Digital Marketplace",
            response.get_data(as_text=True)
        )

    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_have_supplier_name_on_services_page(self, data_api_client):
        data_api_client.get_supplier.return_value = self.load_example_listing("supplier_response")
        data_api_client.find_services.return_value = {'services': []}

        response = self.client.get('/admin/suppliers/services?supplier_id=1000')

        self.assertEquals(200, response.status_code)
        self.assertIn(
            "Supplier Name",
            response.get_data(as_text=True)
        )

    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_show_service_details_on_page(self, data_api_client):
        data_api_client.get_supplier.return_value = self.load_example_listing("supplier_response")
        data_api_client.find_services.return_value = self.load_example_listing("services_response")

        response = self.client.get('/admin/suppliers/services?supplier_id=1000')

        self.assertEquals(200, response.status_code)
        self.assertIn(
            "Contract Management",
            response.get_data(as_text=True)
        )
        self.assertIn(
            '<a href="/g-cloud/services/5687123785023488">',
            response.get_data(as_text=True)
        )
        self.assertIn(
            "5687123785023488",
            response.get_data(as_text=True)
        )
        self.assertIn(
            "G-Cloud 6",
            response.get_data(as_text=True)
        )
        self.assertIn(
            "Software as a Service",
            response.get_data(as_text=True)
        )
        self.assertIn(
            "Public",
            response.get_data(as_text=True)
        )
        self.assertIn(
            '<a href="/admin/services/5687123785023488">',
            response.get_data(as_text=True)
        )
        self.assertIn(
            "Edit",
            response.get_data(as_text=True)
        )

    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_show_correct_fields_for_disabled_service(self, data_api_client):
        data_api_client.get_supplier.return_value = self.load_example_listing("supplier_response")

        services = self.load_example_listing("services_response")
        services["services"][0]["status"] = "disabled"
        data_api_client.find_services.return_value = services

        response = self.client.get('/admin/suppliers/services?supplier_id=1000')

        self.assertEquals(200, response.status_code)
        self.assertIn(
            "Removed",
            response.get_data(as_text=True)
        )
        self.assertIn(
            "Details",
            response.get_data(as_text=True)
        )

    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_show_correct_fields_for_enabled_service(self, data_api_client):
        data_api_client.get_supplier.return_value = self.load_example_listing("supplier_response")

        services = self.load_example_listing("services_response")
        services["services"][0]["status"] = "enabled"
        data_api_client.find_services.return_value = services

        response = self.client.get('/admin/suppliers/services?supplier_id=1000')

        self.assertEquals(200, response.status_code)
        self.assertIn(
            "Private",
            response.get_data(as_text=True)
        )
        self.assertIn(
            "Edit",
            response.get_data(as_text=True)
        )


class TestSupplierInviteUserView(LoggedInApplicationTest):

    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_not_acccept_bad_email_on_invite_user(self, data_api_client):
        data_api_client.get_supplier.return_value = self.load_example_listing("supplier_response")
        data_api_client.find_users.return_value = self.load_example_listing("users_response")

        response = self.client.post(
            "/admin/suppliers/1234/invite-user",
            data={'email_address': 'notatallvalid'},
            follow_redirects=True
        )

        self.assertEquals(400, response.status_code)
        self.assertTrue("Please enter a valid email address" in response.get_data(as_text=True))

    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_not_allow_missing_email_on_invite_user(self, data_api_client):
        data_api_client.get_supplier.return_value = self.load_example_listing("supplier_response")
        data_api_client.find_users.return_value = self.load_example_listing("users_response")

        response = self.client.post(
            "/admin/suppliers/1234/invite-user",
            data={},
            follow_redirects=True
        )

        self.assertEquals(400, response.status_code)
        self.assertTrue("Email can not be empty" in response.get_data(as_text=True))

    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_be_a_404_if_non_int_supplier_id(self, data_api_client):

        response = self.client.post(
            "/admin/suppliers/bad/invite-user",
            data={},
            follow_redirects=True
        )

        self.assertEquals(404, response.status_code)
        self.assertFalse(data_api_client.called)

    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_be_a_404_if_supplier_id_not_found(self, data_api_client):

        data_api_client.get_supplier.side_effect = HTTPError(Response(404))

        response = self.client.post(
            "/admin/suppliers/1234/invite-user",
            data={},
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
            "/admin/suppliers/1234/invite-user",
            data={},
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
            "/admin/suppliers/1234/invite-user",
            data={
                'email_address': 'this@isvalid.com',
            })

        generate_token.assert_called_once_with(
            {
                "supplier_id": 1234,
                "supplier_name": "Supplier Name",
                "email_address": "this@isvalid.com"
            },
            'KEY',
            'SALT'
        )

        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.location, 'http://localhost/admin/suppliers/users?supplier_id=1234')

    @mock.patch('app.main.views.suppliers.generate_token')
    @mock.patch('app.main.views.suppliers.send_email')
    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_create_audit_event(self, data_api_client, send_email, generate_token):
        data_api_client.get_supplier.return_value = self.load_example_listing('supplier_response')
        data_api_client.find_users.return_value = self.load_example_listing('users_response')

        res = self.client.post(
            '/admin/suppliers/1234/invite-user',
            data={
                'email_address': 'email@example.com'
            })

        data_api_client.create_audit_event.assert_called_once_with(
            audit_type=AuditTypes.invite_user,
            user='test@example.com',
            object_type='suppliers',
            object_id=1234,
            data={'invitedEmail': 'email@example.com'})

        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.location, 'http://localhost/admin/suppliers/users?supplier_id=1234')

    @mock.patch('app.main.views.suppliers.generate_token')
    @mock.patch('app.main.views.suppliers.send_email')
    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_not_send_email_if_bad_supplier_id(self, data_api_client, send_email, generate_token):
        data_api_client.get_supplier.side_effect = HTTPError(Response(404))
        data_api_client.find_users.side_effect = HTTPError(Response(404))

        res = self.client.post(
            "/admin/suppliers/1234/invite-user",
            data={
                'email_address': 'this@isvalid.com',
            })

        self.assertFalse(data_api_client.find_users.called)
        self.assertFalse(send_email.called)
        self.assertFalse(generate_token.called)
        self.assertEqual(res.status_code, 404)

    @mock.patch('app.main.views.suppliers.send_email')
    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_call_send_email_with_correct_params(self, data_api_client, send_email):
        data_api_client.get_supplier.return_value = self.load_example_listing("supplier_response")
        data_api_client.find_users.return_value = self.load_example_listing("users_response")

        res = self.client.post(
            "/admin/suppliers/1234/invite-user",
            data={
                'email_address': 'this@isvalid.com',
            }
        )

        send_email.assert_called_once_with(
            'this@isvalid.com',
            mock.ANY,
            'MANDRILL',
            'Your Digital Marketplace invitation',
            'enquiries@digitalmarketplace.service.gov.uk',
            'Digital Marketplace Admin',
            ["user-invite"]
        )

        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.location, 'http://localhost/admin/suppliers/users?supplier_id=1234')

    @mock.patch('app.main.views.suppliers.send_email')
    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_strip_whitespace_surrounding_invite_user_email_address_field(self, data_api_client, send_email):
        data_api_client.get_supplier.return_value = self.load_example_listing("supplier_response")
        data_api_client.find_users.return_value = self.load_example_listing("users_response")

        self.client.post(
            "/admin/suppliers/1234/invite-user",
            data={
                'email_address': '  this@isvalid.com  ',
            }
        )

        send_email.assert_called_once_with(
            'this@isvalid.com',
            mock.ANY,
            mock.ANY,
            mock.ANY,
            mock.ANY,
            mock.ANY,
            mock.ANY
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
            "/admin/suppliers/1234/invite-user",
            data={
                'email_address': 'this@isvalid.com',
            }
        )

        render_template.assert_called_once_with(
            "emails/invite_user_email.html",
            url="http://localhost/suppliers/create-user/token",
            supplier="Supplier Name"
        )

        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.location, 'http://localhost/admin/suppliers/users?supplier_id=1234')

    @mock.patch('app.main.views.suppliers.send_email')
    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_be_a_503_if_email_fails(self, data_api_client, send_email):
        data_api_client.get_supplier.return_value = self.load_example_listing("supplier_response")
        data_api_client.find_users.return_value = self.load_example_listing("users_response")
        send_email.side_effect = MandrillException("Arrrgh")
        res = self.client.post(
            "/admin/suppliers/1234/invite-user",
            data={
                'email_address': 'this@isvalid.com',
            })

        send_email.assert_called_once_with(
            'this@isvalid.com',
            mock.ANY,
            'MANDRILL',
            'Your Digital Marketplace invitation',
            'enquiries@digitalmarketplace.service.gov.uk',
            'Digital Marketplace Admin',
            ["user-invite"]
        )

        self.assertEqual(res.status_code, 503)


@mock.patch('app.main.views.suppliers.data_api_client')
class TestUpdatintSupplierName(LoggedInApplicationTest):
    def test_admin_can_test_update_supplier_name(self, data_api_client):
        data_api_client.get_supplier.return_value = {"suppliers": {"id": 1234, "name": "Something Old"}}
        response = self.client.post(
            '/admin/suppliers/1234/edit/name',
            data={'new_supplier_name': 'Something New'}
        )
        assert response.status_code == 302
        assert response.location == 'http://localhost/admin/suppliers?supplier_id=1234'
        data_api_client.update_supplier.assert_called_once_with(1234, {'name': "Something New"}, "test@example.com")

    def test_ccs_roles_can_not_update_supplier_name(self, data_api_client):
        for role in ('admin-ccs-sourcing', 'admin-ccs-category'):
            self.user_role = role
            response = self.client.post(
                '/admin/suppliers/1234/edit/name',
                data={'new_supplier_name': 'Something New'}
            )
            assert response.status_code == 403
            data_api_client.update_supplier.assert_not_called()


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
            data={'PR1': 'false'})

        declaration = self.load_example_listing('declaration_response')['declaration']
        declaration['PR1'] = False
        declaration['SQ1-3'] = None
        declaration['SQC3'] = None

        data_api_client.set_supplier_declaration.assert_called_with(
            '1234', 'g-cloud-7', declaration, 'test@example.com')


@mock.patch('app.main.views.suppliers.data_api_client')
@mock.patch('app.main.views.suppliers.download_agreement_file')
class TestDownloadSignedAgreementFile(LoggedInApplicationTest):
    user_role = 'admin-ccs-sourcing'

    def test_download_agreement_is_called_with_the_right_parameters(self, download_agreement_file, data_api_client):
        data_api_client.get_supplier_framework_info.return_value = {
            'frameworkInterest': {'agreementPath': '/path/to/file/in/s3/1234-signed-agreement-file.pdf'}
        }
        # Mock out a response from download_agreement_file() - we don't care what it is
        download_agreement_file.side_effect = HTTPError(Response(404))
        self.client.get('/admin/suppliers/1234/agreement/g-cloud-7')
        download_agreement_file.assert_called_once_with('1234', 'g-cloud-7', 'signed-agreement-file.pdf')


@mock.patch('app.main.views.suppliers.data_api_client')
@mock.patch('app.main.views.suppliers.s3')
class TestDownloadAgreementFile(LoggedInApplicationTest):
    user_role = 'admin-ccs-sourcing'

    def test_category_admin_user_should_not_be_able_to_download(self, s3, data_api_client):
        self.user_role = 'admin-ccs-category'

        response = self.client.get('/admin/suppliers/1234/agreements/g-cloud-7/foo.pdf')

        eq_(response.status_code, 403)

    def test_should_404_if_document_does_not_exist(self, s3, data_api_client):
        data_api_client.get_supplier_framework_info.return_value = {
            'frameworkInterest': {'declaration': {'SQ1-1a': 'Supplier name'}}
        }
        s3.S3.return_value.get_signed_url.return_value = None

        response = self.client.get('/admin/suppliers/1234/agreements/g-cloud-7/foo.pdf')

        s3.S3.return_value.get_signed_url.assert_called_with('g-cloud-7/agreements/1234/1234-foo.pdf')
        eq_(response.status_code, 404)

    def test_should_redirect(self, s3, data_api_client):
        data_api_client.get_supplier_framework_info.return_value = {
            'frameworkInterest': {'declaration': {'key': 'Supplier name'}}
        }
        s3.S3.return_value.get_signed_url.return_value = 'http://foo/blah?extra'

        self.app.config['DM_ASSETS_URL'] = 'https://example'

        response = self.client.get('/admin/suppliers/1234/agreements/g-cloud-7/foo.pdf')

        s3.S3.return_value.get_signed_url.assert_called_with('g-cloud-7/agreements/1234/1234-foo.pdf')
        eq_(response.status_code, 302)
        eq_(response.location, 'https://example/blah?extra')

    def test_admin_should_be_able_to_download_countersigned_agreement(self, s3, data_api_client):
        data_api_client.get_supplier_framework_info.return_value = {
            'frameworkInterest': {'declaration': {'key': 'value'}}
        }
        s3.S3.return_value.get_signed_url.return_value = 'http://foo/blah?extra'
        self.app.config['DM_ASSETS_URL'] = 'https://example'

        response = self.client.get(
            '/admin/suppliers/1234/agreements/g-cloud-7/countersigned-framework-agreement.pdf'
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
        data_api_client.get_supplier_framework_info.return_value = \
            {"frameworkInterest": {
                "onFramework": True,
                "agreementStatus": "signed",
                "countersignedPath": "g-cloud-7/agreements/93495/93495-countersigned-framework-agreement.pdf"
            }}

        response = self.client.get('/admin/suppliers/1234/countersigned-agreements/g-cloud-7')
        eq_(response.status_code, 200)

    def test_should_display_no_documents_if_no_documents_listed(self, s3, data_api_client):
        s3.S3.return_value.get_key.return_value = []
        data_api_client.get_supplier_framework_info.return_value = {
            "frameworkInterest": {
                "onFramework": True,
                "agreementStatus": "signed",
                "countersignedPath": None
            }
        }

        response = self.client.get('/admin/suppliers/1234/countersigned-agreements/g-cloud-7')
        self.assertIn(
            'No agreements have been uploaded',
            response.get_data(as_text=True)
        )


@freeze_time('2016-12-25 06:30:01')
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
        data_api_client.get_supplier_framework_info.return_value = \
            {"frameworkInterest": {
                "onFramework": True,
                "agreementStatus": "signed",
                "agreementId": 1212,
                "countersignedPath": "g-cloud-7/agreements/93495/93495-countersigned-framework-agreement.pdf"
            }}

        response = self.client.post('/admin/suppliers/1234/countersigned-agreements/g-cloud-7',
                                    data=dict(
                                        countersigned_agreement=(BytesIO(b"this is a test"),
                                                                 'test.odt'), ), follow_redirects=True)

        self.assertIn(
            'This must be a pdf',
            response.get_data(as_text=True)
        )
        eq_(response.status_code, 200)

    def test_can_upload_countersigned_agreement_for_signed_agreement(self, s3, data_api_client):
        s3.S3.return_value.get_key.return_value = {
            'size': '7050',
            'path': u'g-cloud-7/agreements/1234/1234-countersigned-framework-agreement.pdf',
            'ext': u'pdf',
            'last_modified': u'2016-01-15T12:58:08.000000Z',
            'filename': u'1234-countersigned-framework-agreement'
        }
        data_api_client.get_supplier_framework_info.return_value = \
            {"frameworkInterest": {
                "onFramework": True,
                "agreementStatus": "signed",
                "agreementId": 1212,
                "countersignedPath": None,
                "declaration": {"nameOfOrganisation": "Supplier Mc Supply Face"},
            }}
        response = self.client.post('/admin/suppliers/1234/countersigned-agreements/g-cloud-7',
                                    data=dict(
                                        countersigned_agreement=(BytesIO(b"this is a test"),
                                                                 'countersigned_agreement.pdf'),
                                    ))

        data_api_client.approve_agreement_for_countersignature.assert_called_once_with(
            1212,
            'test@example.com',
            '1234'
        )

        s3.S3.return_value.save.assert_called_once_with(
            "g-cloud-7/agreements/1234/1234-agreement-countersignature-2016-12-25-063001.pdf",
            mock.ANY,
            acl='private',
            move_prefix=None,
            download_filename='Supplier_Mc_Supply_Face-1234-agreement-countersignature.pdf'
        )

        data_api_client.update_framework_agreement.assert_called_once_with(
            1212,
            {"countersignedAgreementPath": "g-cloud-7/agreements/1234/1234-agreement-countersignature-2016-12-25-063001.pdf"},  # noqa
            'test@example.com'
        )

        data_api_client.create_audit_event.assert_called_once_with(
            audit_type=AuditTypes.upload_countersigned_agreement,
            user='test@example.com',
            object_type='suppliers',
            object_id=u'1234',
            data={
                'upload_countersigned_agreement':
                    'g-cloud-7/agreements/1234/1234-agreement-countersignature-2016-12-25-063001.pdf'
                }
        )

        assert response.status_code == 302
        assert response.location == 'http://localhost/admin/suppliers/1234/countersigned-agreements/g-cloud-7'

    def test_can_upload_countersigned_agreement_for_already_countersigned_agreement(self, s3, data_api_client):
        s3.S3.return_value.get_key.return_value = {
            'size': '7050',
            'path': u'g-cloud-7/agreements/1234/1234-countersigned-framework-agreement.pdf',
            'ext': u'pdf',
            'last_modified': u'2016-01-15T12:58:08.000000Z',
            'filename': u'1234-countersigned-framework-agreement'
        }
        data_api_client.get_supplier_framework_info.return_value = \
            {"frameworkInterest": {
                "onFramework": True,
                "agreementStatus": "countersigned",
                "agreementId": 1212,
                "countersignedPath": "g-cloud-7/agreements/1234/1234-agreement-countersignature-2016-12-25-063001.pdf",  # noqa
                "declaration": {"nameOfOrganisation": "Supplier Mc Supply Face"},
            }}
        response = self.client.post('/admin/suppliers/1234/countersigned-agreements/g-cloud-7',
                                    data=dict(
                                        countersigned_agreement=(BytesIO(b"this is a test"),
                                                                 'countersigned_agreement.pdf'),
                                    ))

        data_api_client.approve_agreement_for_countersignature.assert_not_called()

        s3.S3.return_value.save.assert_called_once_with(
            "g-cloud-7/agreements/1234/1234-agreement-countersignature-2016-12-25-063001.pdf",
            mock.ANY,
            acl='private',
            move_prefix=None,
            download_filename='Supplier_Mc_Supply_Face-1234-agreement-countersignature.pdf'
        )

        data_api_client.update_framework_agreement.assert_called_once_with(
            1212,
            {"countersignedAgreementPath": "g-cloud-7/agreements/1234/1234-agreement-countersignature-2016-12-25-063001.pdf"},  # noqa
            'test@example.com'
        )

        data_api_client.create_audit_event.assert_called_once_with(
            audit_type=AuditTypes.upload_countersigned_agreement,
            user='test@example.com',
            object_type='suppliers',
            object_id=u'1234',
            data={
                'upload_countersigned_agreement':
                    'g-cloud-7/agreements/1234/1234-agreement-countersignature-2016-12-25-063001.pdf'}
        )

        assert response.status_code == 302
        assert response.location == 'http://localhost/admin/suppliers/1234/countersigned-agreements/g-cloud-7'

    def test_can_upload_countersigned_agreement_for_framework_without_declaration(self, s3, data_api_client):
        s3.S3.return_value.get_key.return_value = {
            'size': '7050',
            'path': u'g-cloud-7/agreements/1234/1234-countersigned-framework-agreement.pdf',
            'ext': u'pdf',
            'last_modified': u'2016-01-15T12:58:08.000000Z',
            'filename': u'1234-countersigned-framework-agreement'
        }
        data_api_client.get_supplier_framework_info.return_value = \
            {"frameworkInterest": {
                "onFramework": True,
                "agreementStatus": "signed",
                "agreementId": 1212,
                "countersignedPath": None
            }}
        data_api_client.get_supplier.return_value = \
            {"suppliers": {
                "name": "DM Supplier Name"
            }}
        response = self.client.post('/admin/suppliers/1234/countersigned-agreements/g-cloud-7',
                                    data=dict(
                                        countersigned_agreement=(BytesIO(b"this is a test"),
                                                                 'countersigned_agreement.pdf'),
                                    ))

        data_api_client.approve_agreement_for_countersignature.assert_called_once_with(
            1212,
            'test@example.com',
            '1234'
        )

        s3.S3.return_value.save.assert_called_once_with(
            "g-cloud-7/agreements/1234/1234-agreement-countersignature-2016-12-25-063001.pdf",
            mock.ANY,
            acl='private',
            move_prefix=None,
            download_filename='DM_Supplier_Name-1234-agreement-countersignature.pdf'
        )

        data_api_client.update_framework_agreement.assert_called_once_with(
            1212,
            {
                "countersignedAgreementPath": "g-cloud-7/agreements/1234/1234-agreement-countersignature-2016-12-25-063001.pdf"},  # noqa
            'test@example.com'
        )

        assert response.status_code == 302
        assert response.location == 'http://localhost/admin/suppliers/1234/countersigned-agreements/g-cloud-7'
        data_api_client.create_audit_event.assert_called_once_with(
            audit_type=AuditTypes.upload_countersigned_agreement,
            user='test@example.com',
            object_type='suppliers',
            object_id=u'1234',
            data={
                'upload_countersigned_agreement':
                    'g-cloud-7/agreements/1234/1234-agreement-countersignature-2016-12-25-063001.pdf'
            }
        )


@mock.patch('app.main.views.suppliers.data_api_client')
@mock.patch('app.main.views.suppliers.s3')
class TestRemoveCountersignedAgreementFile(LoggedInApplicationTest):
    user_role = 'admin-ccs-sourcing'

    def test_should_remove_countersigned_agreement(self, s3, data_api_client):
        s3.S3.return_value.delete_key.return_value = {'Key': 'digitalmarketplace-documents-dev-dev'
                                                      ',g-cloud-7/agreements/93495/93495-'
                                                      'countersigned-framework-agreement.pdf'}
        response = self.client.post('/admin/suppliers/1234/countersigned-agreements-remove/g-cloud-7')
        eq_(response.status_code, 302)

    def test_admin_should_not_be_able_to_remove_countersigned_agreement(self, s3, data_api_client):
        self.user_role = 'admin'
        s3.S3.return_value.delete_key.return_value = {'Key': 'digitalmarketplace-documents-dev-dev'
                                                      ',g-cloud-7/agreements/93495/93495-'
                                                      'countersigned-framework-agreement.pdf'}
        response = self.client.post('/admin/suppliers/1234/countersigned-agreements-remove/g-cloud-7')
        eq_(response.status_code, 403)

    def test_should_display_remove_countersigned_agreement_message(self, s3, data_api_client):
        s3.S3.return_value.get_key.return_value = {
            'size': '7050',
            'path': u'g-cloud-7/agreements/93495/93495-countersigned-framework-agreement.pdf',
            'ext': u'pdf',
            'last_modified': u'2016-01-15T12:58:08.000000Z',
            'filename': u'93495-countersigned-framework-agreement'
        }
        data_api_client.get_supplier_framework_info.return_value = \
            {"frameworkInterest": {
                "onFramework": True,
                "agreementStatus": "signed",
                "countersignedPath": "g-cloud-7/agreements/93495/93495-countersigned-framework-agreement.pdf"
            }}
        response = self.client.get('/admin/suppliers/1234/countersigned-agreements-remove/g-cloud-7',
                                   follow_redirects=True)
        self.assertIn(
            'Do you want to remove the countersigned agreement?',
            response.get_data(as_text=True)
        )
        eq_(response.status_code, 200)


@mock.patch('app.main.views.suppliers.data_api_client')
@mock.patch('app.main.views.suppliers.s3')
class TestViewingASupplierDeclaration(LoggedInApplicationTest):
    user_role = 'admin-ccs-sourcing'

    def test_should_404_if_supplier_does_not_exist(self, s3, data_api_client):
        data_api_client.get_supplier.side_effect = APIError(Response(404))

        response = self.client.get('/admin/suppliers/1234/agreements/g-cloud-8')

        eq_(response.status_code, 404)
        data_api_client.get_supplier.assert_called_with('1234')
        assert not data_api_client.get_framework.called

    def test_should_404_if_framework_does_not_exist(self, s3, data_api_client):
        data_api_client.get_supplier.return_value = self.load_example_listing('supplier_response')
        data_api_client.get_framework.side_effect = APIError(Response(404))

        response = self.client.get('/admin/suppliers/1234/agreements/g-cloud-8')

        eq_(response.status_code, 404)
        data_api_client.get_supplier.assert_called_with('1234')
        data_api_client.get_framework.assert_called_with('g-cloud-8')

    def test_should_404_if_agreement_not_returned(self, s3, data_api_client):
        data_api_client.get_supplier.return_value = self.load_example_listing('supplier_response')
        data_api_client.get_framework.return_value = self.load_example_listing('framework_response')
        not_returned = self.load_example_listing('supplier_framework_response')
        not_returned['frameworkInterest']['agreementReturned'] = False
        data_api_client.get_supplier_framework_info.return_value = not_returned
        response = self.client.get('/admin/suppliers/1234/agreements/g-cloud-8')

        eq_(response.status_code, 404)
        data_api_client.get_supplier.assert_called_with('1234')
        data_api_client.get_framework.assert_called_with('g-cloud-8')
        data_api_client.get_supplier_framework_info.assert_called_with('1234', 'g-cloud-8')

    def test_should_show_agreement_details_on_page(self, s3, data_api_client):
        data_api_client.get_supplier.return_value = self.load_example_listing('supplier_response')
        data_api_client.get_framework.return_value = self.load_example_listing('framework_response')
        data_api_client.get_supplier_framework_info.return_value = self.load_example_listing(
            'supplier_framework_response'
        )

        def find_services_iter_side_effect(*args, **kwargs):
            assert int(kwargs["supplier_id"]) == 1234
            assert kwargs["framework"] == "g-cloud-8"
            # very minimal fake services
            return iter((
                {
                    "id": 1111,
                    "lotSlug": "dried-fruit",
                    "lotName": "Raisins & dates",
                },
                {
                    "id": 2222,
                    "lotSlug": "salad",
                    "lotName": "Lettuce & cucumber",
                },
                {
                    "id": 3333,
                    "lotSlug": "dried-fruit",
                    "lotName": "Raisins & dates",
                },
            ))
        data_api_client.find_services_iter.side_effect = find_services_iter_side_effect

        with mock.patch('app.main.views.suppliers.get_signed_url') as mock_get_url:
            mock_get_url.return_value = "http://example.com/document/1234.pdf"

            response = self.client.get('/admin/suppliers/1234/agreements/g-cloud-8')
            document = html.fromstring(response.get_data(as_text=True))
            eq_(response.status_code, 200)
            # Registered Address
            assert len(document.xpath('//li[contains(text(), "Corsewall Lighthouse")]')) == 1
            assert len(document.xpath('//li[contains(text(), "Stranraer")]')) == 1
            assert len(document.xpath('//li[contains(text(), "DG9 0QG")]')) == 1
            # Company number - linked
            assert len(document.xpath('//a[@href="https://beta.companieshouse.gov.uk/company/1234456"][contains(text(), "1234456")]')) == 1  # noqa
            # Lots
            assert len(document.xpath('//li[contains(text(), "Lettuce & cucumber")]')) == 1
            assert len(document.xpath('//li[contains(text(), "Raisins & dates")]')) == 1
            # Signer details
            assert len(document.xpath('//p[contains(text(), "Signer Name")]')) == 1
            assert len(document.xpath('//p[contains(text(), "Ace Developer")]')) == 1
            # Uploader details
            assert len(document.xpath('//p[contains(text(), "Uploader Name")]')) == 1
            assert len(document.xpath('//span[contains(text(), "uploader@email.com")]')) == 1

    def test_should_embed_for_pdf_file(self, s3, data_api_client):
        data_api_client.get_supplier.return_value = self.load_example_listing('supplier_response')
        data_api_client.get_framework.return_value = self.load_example_listing('framework_response')
        data_api_client.get_supplier_framework_info.return_value = self.load_example_listing(
            'supplier_framework_response'
        )

        with mock.patch('app.main.views.suppliers.get_signed_url') as mock_get_url:
            mock_get_url.return_value = "http://example.com/document/1234.pdf"
            response = self.client.get('/admin/suppliers/1234/agreements/g-cloud-8')
            document = html.fromstring(response.get_data(as_text=True))
            eq_(response.status_code, 200)
            assert len(document.xpath('//embed[@src="http://example.com/document/1234.pdf"]')) == 1
            assert len(document.xpath('//img[@src="http://example.com/document/1234.pdf"]')) == 0

    def test_should_img_for_image_file(self, s3, data_api_client):
        data_api_client.get_supplier.return_value = self.load_example_listing('supplier_response')
        data_api_client.get_framework.return_value = self.load_example_listing('framework_response')
        supplier_framework_info = self.load_example_listing(
            'supplier_framework_response'
        )
        supplier_framework_info['frameworkInterest']['agreementPath'] = 'path/to/img.jpg'
        data_api_client.get_supplier_framework_info.return_value = supplier_framework_info

        with mock.patch('app.main.views.suppliers.get_signed_url') as mock_get_url:
            mock_get_url.return_value = "http://example.com/document/1234.png"
            response = self.client.get('/admin/suppliers/1234/agreements/g-cloud-8')
            document = html.fromstring(response.get_data(as_text=True))
            eq_(response.status_code, 200)
            assert len(document.xpath('//img[@src="http://example.com/document/1234.png"]')) == 1
            assert len(document.xpath('//embed[@src="http://example.com/document/1234.png"]')) == 0


@mock.patch('app.main.views.suppliers.data_api_client')
class TestPutSignedAgreementOnHold(LoggedInApplicationTest):
    user_role = 'admin-ccs-sourcing'

    @property
    def put_signed_agreement_on_hold_return_value(self):
        # a property so we always get a clean *copy* of this to work with
        return {
            "agreement": {
                "id": 123,
                "supplierId": 4321,
                "frameworkSlug": "g-cloud-99-flake",
            },
        }

    def test_it_fails_if_not_ccs_admin(self, data_api_client):
        self.user_role = 'admin'
        data_api_client.put_signed_agreement_on_hold.return_value = self.put_signed_agreement_on_hold_return_value
        res = self.client.post('/admin/suppliers/agreements/123/on-hold', data={"nameOfOrganisation": "Test"})

        assert not data_api_client.put_signed_agreement_on_hold.called
        assert res.status_code == 403

    def test_happy_path(self, data_api_client):
        data_api_client.put_signed_agreement_on_hold.return_value = self.put_signed_agreement_on_hold_return_value
        res = self.client.post(
            "/admin/suppliers/agreements/123/on-hold",
            data={"nameOfOrganisation": "Test"},
        )

        data_api_client.put_signed_agreement_on_hold.assert_called_once_with('123', 'test@example.com')
        assert_flashes(self, "The agreement for Test was put on hold.")
        assert res.status_code == 302

        parsed_location = urlparse(res.location)
        assert parsed_location.path == "/admin/suppliers/4321/agreements/g-cloud-99-flake/next"
        assert parse_qs(parsed_location.query) == {}

    def test_happy_path_with_next_status(self, data_api_client):
        data_api_client.put_signed_agreement_on_hold.return_value = self.put_signed_agreement_on_hold_return_value
        res = self.client.post(
            "/admin/suppliers/agreements/123/on-hold?next_status=on-hold",
            data={"nameOfOrganisation": "Test"},
        )

        data_api_client.put_signed_agreement_on_hold.assert_called_once_with('123', 'test@example.com')
        assert_flashes(self, "The agreement for Test was put on hold.")
        assert res.status_code == 302

        parsed_location = urlparse(res.location)
        assert parsed_location.path == "/admin/suppliers/4321/agreements/g-cloud-99-flake/next"
        assert parse_qs(parsed_location.query) == {"status": ["on-hold"]}


@mock.patch('app.main.views.suppliers.data_api_client')
class TestApproveAgreement(LoggedInApplicationTest):
    user_role = 'admin-ccs-sourcing'

    @property
    def put_signed_agreement_on_hold_return_value(self):
        # a property so we always get a clean *copy* of this to work with
        return {
            "agreement": {
                "id": 123,
                "supplierId": 4321,
                "frameworkSlug": "g-cloud-99p-world",
            },
        }

    def test_it_fails_if_not_ccs_admin(self, data_api_client):
        self.user_role = 'admin'
        data_api_client.approve_agreement_for_countersignature.return_value = \
            self.put_signed_agreement_on_hold_return_value
        res = self.client.post('/admin/suppliers/agreements/123/approve', data={"nameOfOrganisation": "Test"})

        assert not data_api_client.approve_agreement_for_countersignature.called
        assert res.status_code == 403

    def test_happy_path(self, data_api_client):
        data_api_client.approve_agreement_for_countersignature.return_value = \
            self.put_signed_agreement_on_hold_return_value
        res = self.client.post(
            "/admin/suppliers/agreements/123/approve",
            data={"nameOfOrganisation": "Test"},
        )

        data_api_client.approve_agreement_for_countersignature.assert_called_once_with('123',
                                                                                       'test@example.com',
                                                                                       '1234')
        assert_flashes(self, "The agreement for Test was approved. They will receive a countersigned version soon.")
        assert res.status_code == 302

        parsed_location = urlparse(res.location)
        assert parsed_location.path == "/admin/suppliers/4321/agreements/g-cloud-99p-world/next"
        assert parse_qs(parsed_location.query) == {}

    def test_happy_path_with_next_status(self, data_api_client):
        data_api_client.approve_agreement_for_countersignature.return_value = \
            self.put_signed_agreement_on_hold_return_value
        res = self.client.post(
            "/admin/suppliers/agreements/123/approve?next_status=on-hold",
            data={"nameOfOrganisation": "Test"},
        )

        data_api_client.approve_agreement_for_countersignature.assert_called_once_with('123',
                                                                                       'test@example.com',
                                                                                       '1234')
        assert_flashes(self, "The agreement for Test was approved. They will receive a countersigned version soon.")
        assert res.status_code == 302

        parsed_location = urlparse(res.location)
        assert parsed_location.path == "/admin/suppliers/4321/agreements/g-cloud-99p-world/next"
        assert parse_qs(parsed_location.query) == {"status": ["on-hold"]}


@mock.patch('app.main.views.suppliers.data_api_client')
@mock.patch('app.main.views.suppliers.get_signed_url')
@mock.patch('app.main.views.suppliers.s3')
class TestCorrectButtonsAreShownDependingOnContext(LoggedInApplicationTest):
    user_role = 'admin-ccs-sourcing'

    def set_mocks(self, s3, get_signed_url, data_api_client, **kwargs):
        data_api_client.get_supplier.return_value = {
            'suppliers': {
                "id": 1234,
            },
        }
        data_api_client.get_framework.return_value = {
            'frameworks': {
                'frameworkAgreementVersion': 'v1.0',
                "slug": "g-cloud-8",
            },
        }
        data_api_client.get_supplier_framework_info.return_value = {
            'frameworkInterest': {
                'agreementReturned': True,
                'agreementStatus': kwargs['agreement_status'],
                'agreementId': 4321,
                'declaration': '',
                'agreementDetails': {},
                'agreementPath': 'g-cloud-8/1234/1234-file.pdf',
                'countersignedDetails': {},
                "supplierId": 1234,
                "frameworkSlug": "g-cloud-8",
            }
        }
        data_api_client.find_services_iter.return_value = []
        get_signed_url.return_value = '#'
        s3.S3.return_value.list.return_value = [
            {'path': 'g-cloud-8/agreements/4321/4321-signed-framework-agreement.png',
             'ext': 'pdf'}
        ]

    @staticmethod
    def _parsed_url_matches(url, path_matches=None, qd_matches=None):
        parsed_url = urlparse(url)
        return (
            path_matches is None or parsed_url.path == path_matches
        ) and (
            qd_matches is None or parse_qs(parsed_url.query) == qd_matches
        )

    def test_none_shown_if_user_not_ccs_admin(self, s3, get_signed_url, data_api_client):
        self.user_role = 'admin'
        self.set_mocks(s3, get_signed_url, data_api_client, agreement_status='signed')

        res = self.client.get('/admin/suppliers/1234/agreements/g-cloud-8')
        assert res.status_code == 200

        data = res.get_data(as_text=True)
        document = html.fromstring(data)

        assert "Accept and continue" not in data
        assert "Put on hold and continue" not in data

        assert not document.xpath("//h2[normalize-space(string())='Accepted by']")

        next_a_elems = document.xpath("//a[normalize-space(string())='Next agreement']")
        assert len(next_a_elems) == 1
        assert self._parsed_url_matches(
            next_a_elems[0].attrib["href"],
            "/admin/suppliers/1234/agreements/g-cloud-8/next",
            {},
        )

    def test_both_shown_if_ccs_admin_and_agreement_signed(self, s3, get_signed_url, data_api_client):
        self.set_mocks(s3, get_signed_url, data_api_client, agreement_status='signed')

        res = self.client.get('/admin/suppliers/1234/agreements/g-cloud-8')
        assert res.status_code == 200

        data = res.get_data(as_text=True)
        document = html.fromstring(data)

        accept_input_elems = document.xpath("//form//input[@type='submit'][@value='Accept and continue']")
        assert len(accept_input_elems) == 1
        accept_form_elem = accept_input_elems[0].xpath("ancestor::form")[0]
        assert self._parsed_url_matches(
            accept_form_elem.attrib["action"],
            "/admin/suppliers/agreements/4321/approve",
            {},
        )
        assert accept_form_elem.attrib["method"].lower() == "post"

        hold_input_elems = document.xpath("//form//input[@type='submit'][@value='Put on hold and continue']")
        assert len(hold_input_elems) == 1
        hold_form_elem = hold_input_elems[0].xpath("ancestor::form")[0]
        assert self._parsed_url_matches(
            hold_form_elem.attrib["action"],
            "/admin/suppliers/agreements/4321/on-hold",
            {},
        )
        assert hold_form_elem.attrib["method"].lower() == "post"

        assert not document.xpath("//h2[normalize-space(string())='Accepted by']")

        next_a_elems = document.xpath("//a[normalize-space(string())='Next agreement']")
        assert len(next_a_elems) == 1
        assert self._parsed_url_matches(
            next_a_elems[0].attrib["href"],
            "/admin/suppliers/1234/agreements/g-cloud-8/next",
            {},
        )

    def test_both_shown_with_status_if_ccs_admin_and_agreement_signed(self, s3, get_signed_url, data_api_client):
        self.set_mocks(s3, get_signed_url, data_api_client, agreement_status='signed')

        res = self.client.get('/admin/suppliers/1234/agreements/g-cloud-8?next_status=approved,countersigned')
        assert res.status_code == 200

        data = res.get_data(as_text=True)
        document = html.fromstring(data)

        accept_input_elems = document.xpath("//form//input[@type='submit'][@value='Accept and continue']")
        assert len(accept_input_elems) == 1
        accept_form_elem = accept_input_elems[0].xpath("ancestor::form")[0]
        assert self._parsed_url_matches(
            accept_form_elem.attrib["action"],
            "/admin/suppliers/agreements/4321/approve",
            {"next_status": ["approved,countersigned"]},
        )
        assert accept_form_elem.attrib["method"].lower() == "post"

        hold_input_elems = document.xpath("//form//input[@type='submit'][@value='Put on hold and continue']")
        assert len(hold_input_elems) == 1
        hold_form_elem = hold_input_elems[0].xpath("ancestor::form")[0]
        assert self._parsed_url_matches(
            hold_form_elem.attrib["action"],
            "/admin/suppliers/agreements/4321/on-hold",
            {"next_status": ["approved,countersigned"]},
        )
        assert hold_form_elem.attrib["method"].lower() == "post"

        assert not document.xpath("//h2[normalize-space(string())='Accepted by']")

        next_a_elems = document.xpath("//a[normalize-space(string())='Next agreement']")
        assert len(next_a_elems) == 1
        assert self._parsed_url_matches(
            next_a_elems[0].attrib["href"],
            "/admin/suppliers/1234/agreements/g-cloud-8/next",
            {"status": ["approved,countersigned"]},
        )

    def test_only_counter_sign_shown_if_agreement_on_hold(self, s3, get_signed_url, data_api_client):
        self.set_mocks(s3, get_signed_url, data_api_client, agreement_status='on-hold')

        res = self.client.get('/admin/suppliers/1234/agreements/g-cloud-8')
        assert res.status_code == 200

        data = res.get_data(as_text=True)
        document = html.fromstring(data)

        accept_input_elems = document.xpath("//form//input[@type='submit'][@value='Accept and continue']")
        assert len(accept_input_elems) == 1
        accept_form_elem = accept_input_elems[0].xpath("ancestor::form")[0]
        assert self._parsed_url_matches(
            accept_form_elem.attrib["action"],
            "/admin/suppliers/agreements/4321/approve",
            {},
        )
        assert accept_form_elem.attrib["method"].lower() == "post"

        assert "Put on hold and continue" not in data
        assert not document.xpath("//h2[normalize-space(string())='Accepted by']")

        next_a_elems = document.xpath("//a[normalize-space(string())='Next agreement']")
        assert len(next_a_elems) == 1
        assert self._parsed_url_matches(
            next_a_elems[0].attrib["href"],
            "/admin/suppliers/1234/agreements/g-cloud-8/next",
            {},
        )

    def test_none_shown_if_agreement_approved(self, s3, get_signed_url, data_api_client):
        self.set_mocks(s3, get_signed_url, data_api_client, agreement_status='approved')

        res = self.client.get('/admin/suppliers/1234/agreements/g-cloud-8')
        assert res.status_code == 200

        data = res.get_data(as_text=True)
        document = html.fromstring(data)

        assert "Accept and continue" not in data
        assert "Put on hold and continue" not in data
        assert len(document.xpath("//h2[normalize-space(string())='Accepted by']")) == 1

        next_a_elems = document.xpath("//a[normalize-space(string())='Next agreement']")
        assert len(next_a_elems) == 1
        assert self._parsed_url_matches(
            next_a_elems[0].attrib["href"],
            "/admin/suppliers/1234/agreements/g-cloud-8/next",
            {},
        )

    def test_none_shown_if_agreement_countersigned(self, s3, get_signed_url, data_api_client):
        self.set_mocks(s3, get_signed_url, data_api_client, agreement_status='countersigned')

        res = self.client.get('/admin/suppliers/1234/agreements/g-cloud-8')
        assert res.status_code == 200

        data = res.get_data(as_text=True)
        document = html.fromstring(data)

        assert "Accept and continue" not in data
        assert "Put on hold and continue" not in data
        assert len(document.xpath("//h2[normalize-space(string())='Accepted by']")) == 1

        next_a_elems = document.xpath("//a[normalize-space(string())='Next agreement']")
        assert len(next_a_elems) == 1
        assert self._parsed_url_matches(
            next_a_elems[0].attrib["href"],
            "/admin/suppliers/1234/agreements/g-cloud-8/next",
            {},
        )
