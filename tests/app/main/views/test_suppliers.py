try:
    from urlparse import urlsplit
    from StringIO import StringIO
except ImportError:
    from urllib.parse import urlsplit
    from io import BytesIO as StringIO
import mock
from dmutils.apiclient.errors import HTTPError
from ...helpers import LoggedInApplicationTest, Response


class TestSupplierView(LoggedInApplicationTest):

    # Supplier Users

    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_404_if_no_supplier_does_not_exist(self, data_api_client):
        data_api_client.get_supplier.side_effect = HTTPError(Response(404))
        response = self.client.get('/admin/suppliers/users?supplier_id=999')
        self.assertEquals(404, response.status_code)

    def test_should_404_if_no_supplier_id(self):
        response = self.client.get('/admin/suppliers/users')
        self.assertEquals(404, response.status_code)

    def test_should_400_if_invalid_supplier_id(self):
        response = self.client.get('/admin/suppliers/users?supplier_id=invalid')
        self.assertEquals(400, response.status_code)

    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_call_apis_with_supplier_id(self, data_api_client):
        data_api_client.get_supplier.return_value = {'suppliers': {}}
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
            "09:33:53",
            response.get_data(as_text=True)
        )
        self.assertIn(
            "23/07/2015",
            response.get_data(as_text=True)
        )
        self.assertIn(
            "12:46:01",
            response.get_data(as_text=True)
        )
        self.assertIn(
            "29/06/2015",
            response.get_data(as_text=True)
        )
        self.assertIn(
            "No",
            response.get_data(as_text=True)
        )

        self.assertIn(
            '<button class="button-destructive">Deactivate</button>',
            response.get_data(as_text=True)
        )

        self.assertIn(
            '<form action="/admin/suppliers/users/999/deactivate" method="post">',
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
            '<button class="button-secondary">Unlock</button>',
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
            '<button class="button-secondary">Activate</button>',
            response.get_data(as_text=True)
        )

    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_call_api_to_unlock_user(self, data_api_client):
        data_api_client.get_supplier.return_value = self.load_example_listing("supplier_response")
        data_api_client.update_user.return_value = self.load_example_listing("user_response")

        response = self.client.post('/admin/suppliers/users/999/unlock')

        data_api_client.update_user.assert_called_with(999, locked=False)

        self.assertEquals(302, response.status_code)
        self.assertEquals("http://localhost/admin/suppliers/users?supplier_id=1000", response.location)

    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_call_api_to_activate_user(self, data_api_client):
        data_api_client.get_supplier.return_value = self.load_example_listing("supplier_response")
        data_api_client.update_user.return_value = self.load_example_listing("user_response")

        response = self.client.post('/admin/suppliers/users/999/activate')

        data_api_client.update_user.assert_called_with(999, active=True)

        self.assertEquals(302, response.status_code)
        self.assertEquals("http://localhost/admin/suppliers/users?supplier_id=1000", response.location)

    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_call_api_to_deactivate_user(self, data_api_client):
        data_api_client.get_supplier.return_value = self.load_example_listing("supplier_response")
        data_api_client.update_user.return_value = self.load_example_listing("user_response")

        response = self.client.post('/admin/suppliers/users/999/deactivate')

        data_api_client.update_user.assert_called_with(999, active=False)

        self.assertEquals(302, response.status_code)
        self.assertEquals("http://localhost/admin/suppliers/users?supplier_id=1000", response.location)

    # Supplier Services

    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_should_404_if_supplier_does_not_exist_on_services(self, data_api_client):
        data_api_client.get_supplier.side_effect = HTTPError(Response(404))
        response = self.client.get('/admin/suppliers/services?supplier_id=999')
        self.assertEquals(404, response.status_code)

    def test_should_404_if_no_supplier_id_on_services(self):
        response = self.client.get('/admin/suppliers/users')
        self.assertEquals(404, response.status_code)

    def test_should_400_if_invalid_supplier_id_on_services(self):
        response = self.client.get('/admin/suppliers/services?supplier_id=invalid')
        self.assertEquals(400, response.status_code)

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
            "This supplier has no services on the digital marketplace",
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
            '<a href="/service/5687123785023488">',
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
            "SaaS",
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
