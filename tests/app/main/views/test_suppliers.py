from io import BytesIO
from urllib.parse import urlparse, parse_qs

import mock
import pytest
from dmapiclient import HTTPError, APIError
from dmapiclient.audit import AuditTypes
from dmutils.email.exceptions import EmailError
from flask import current_app
from freezegun import freeze_time
from lxml import html

from ...helpers import LoggedInApplicationTest, Response


class TestSuppliersListView(LoggedInApplicationTest):

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.suppliers.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    @pytest.mark.parametrize("role,expected_code", [
        ("admin", 200),
        ("admin-ccs-category", 200),
        ("admin-ccs-sourcing", 200),
        ("admin-framework-manager", 200),
        ("admin-manager", 403),
    ])
    def test_supplier_list_is_shown_to_users_with_right_roles(self, role, expected_code):
        self.user_role = role
        self.data_api_client.find_suppliers.return_value = {
            "suppliers": [{"id": "12345"}]
        }
        response = self.client.get('/admin/suppliers?supplier_name_prefix=foo')
        actual_code = response.status_code
        assert actual_code == expected_code, "Unexpected response {} for role {}".format(actual_code, role)

    @pytest.mark.parametrize("role, link_should_be_visible", [
        ("admin", True),
        ("admin-ccs-category", True),
        ("admin-ccs-sourcing", False),
        ("admin-framework-manager", True),
    ])
    def test_services_link_is_shown_to_users_with_right_roles(self, role, link_should_be_visible):
        self.user_role = role
        self.data_api_client.find_suppliers.return_value = {
            "suppliers": [{"id": "12345"}]
        }
        response = self.client.get('/admin/suppliers?supplier_name_prefix=foo')
        data = response.get_data(as_text=True)
        link_is_visible = "Services" in data and "/admin/suppliers/12345/services" in data

        assert link_is_visible is link_should_be_visible, (
            "Role {} {} see the link".format(role, "can not" if link_should_be_visible else "can")
        )

    @pytest.mark.parametrize("role, link_should_be_visible", [
        ("admin", True),
        ("admin-ccs-category", True),
        ("admin-framework-manager", False),
    ])
    def test_change_name_link_is_shown_to_users_with_right_roles(self, role, link_should_be_visible):
        self.user_role = role
        self.data_api_client.find_suppliers.return_value = {
            "suppliers": [{"id": "12345"}]
        }
        response = self.client.get('/admin/suppliers?supplier_name_prefix=foo')
        data = response.get_data(as_text=True)
        link_is_visible = "Change name" in data and "/admin/suppliers/12345/edit/name" in data

        assert link_is_visible is link_should_be_visible, (
            "Role {} {} see the link".format(role, "can not" if link_should_be_visible else "can")
        )

    @pytest.mark.parametrize("role, links_should_be_visible", [
        ("admin", False),
        ("admin-ccs-category", False),
        ("admin-ccs-sourcing", True),
        ("admin-framework-manager", False),
    ])
    def test_declaration_and_agreement_links_visible_for_ccs_sourcing(self, role,
                                                                      links_should_be_visible):
        self.user_role = role
        self.data_api_client.find_suppliers.return_value = {
            "suppliers": [{"id": "12345"}]
        }
        response = self.client.get('/admin/suppliers?supplier_name_prefix=foo')
        data = response.get_data(as_text=True)
        document = html.fromstring(data)

        headings = [header.strip() for header in document.xpath('//thead//th/text()')]
        assert links_should_be_visible is (headings == ['Name', 'G-Cloud 7', 'Digital Outcomes and Specialists',
                                                        'G-Cloud 8', 'Digital Outcomes and Specialists 2', 'G-Cloud 9',
                                                        'G-Cloud 10'])

        if links_should_be_visible:
            g_cloud_10_edit_declaration = ''.join(document.xpath('//tbody//tr[2]/td[6]//text()')).strip()
            assert g_cloud_10_edit_declaration == 'Edit G-Cloud 10 declaration'

            g_cloud_10_edit_declaration = ''.join(document.xpath('//tbody//tr[3]/td[6]//text()')).strip()
            assert g_cloud_10_edit_declaration == 'View agreement for G-Cloud 10'

    def test_should_raise_http_error_from_api(self):
        self.data_api_client.find_suppliers.side_effect = HTTPError(Response(404))
        response = self.client.get('/admin/suppliers')
        assert response.status_code == 404

    def test_should_list_suppliers(self):
        self.data_api_client.find_suppliers.return_value = {
            "suppliers": [
                {"id": 1234, "name": "Supplier 1"},
                {"id": 1235, "name": "Supplier 2"},
            ]
        }
        self.data_api_client.get_supplier_framework_info.side_effect = [
            {"frameworkInterest": {"agreementPath": "path/the/first/1234-g7-agreement.pdf"}},
            {"frameworkInterest": {"agreementPath": None}},  # Supplier 1234 has not returned their DOS agreement yet
            HTTPError(Response(404)),                        # Supplier 1235 is not on G-Cloud 7
            {"frameworkInterest": {"agreementPath": "path/the/third/1235-dos-agreement.jpg"}},
        ]
        response = self.client.get("/admin/suppliers")
        document = html.fromstring(response.get_data(as_text=True))

        assert response.status_code == 200
        assert len(document.cssselect('.summary-item-row')) == 2

    def test_should_search_by_prefix(self):
        self.data_api_client.find_suppliers.side_effect = HTTPError(Response(404))
        self.client.get("/admin/suppliers?supplier_name_prefix=foo")

        self.data_api_client.find_suppliers.assert_called_once_with(prefix="foo", duns_number=None)

    def test_should_search_by_duns_number(self):
        self.data_api_client.find_suppliers.side_effect = HTTPError(Response(404))
        self.client.get("/admin/suppliers?supplier_duns_number=987654321")

        self.data_api_client.find_suppliers.assert_called_once_with(prefix=None, duns_number="987654321")

    def test_should_find_by_supplier_id(self):
        self.data_api_client.get_supplier.side_effect = HTTPError(Response(404))
        self.client.get("/admin/suppliers?supplier_id=12345")

        self.data_api_client.get_supplier.assert_called_once_with("12345")


class TestSupplierUsersView(LoggedInApplicationTest):

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.suppliers.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()
        self.data_api_client.get_supplier.return_value = self.load_example_listing("supplier_response")
        self.data_api_client.find_users_iter.return_value = self.load_example_listing("users_response")['users']

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    @pytest.mark.parametrize("role,expected_code", [
        ("admin", 200),
        ("admin-ccs-category", 200),
        ("admin-ccs-sourcing", 403),
        ("admin-framework-manager", 200),
        ("admin-manager", 403),
    ])
    def test_supplier_users_accessible_to_users_with_right_roles(self, role, expected_code):
        self.user_role = role
        response = self.client.get('/admin/suppliers/users?supplier_id=1000')
        actual_code = response.status_code
        assert actual_code == expected_code, "Unexpected response {} for role {}".format(actual_code, role)

    @pytest.mark.parametrize("role, can_edit", [
        ("admin", True),
        ("admin-ccs-category", False),
        ("admin-framework-manager", False),
    ])
    def test_supplier_users_only_editable_for_users_with_right_roles(self, role, can_edit):
        self.user_role = role

        response = self.client.get('/admin/suppliers/users?supplier_id=1000')
        assert response.status_code == 200
        document = html.fromstring(response.get_data(as_text=True))
        deactivate_buttons = document.xpath('.//input[contains(@value, "Deactivate")]')
        assert len(deactivate_buttons) == (1 if can_edit else 0)

    def test_should_404_if_no_supplier_does_not_exist(self):
        self.data_api_client.get_supplier.side_effect = HTTPError(Response(404))
        response = self.client.get('/admin/suppliers/users?supplier_id=999')
        assert response.status_code == 404

    def test_should_404_if_no_supplier_id(self):
        response = self.client.get('/admin/suppliers/users')
        assert response.status_code == 404

    def test_should_call_apis_with_supplier_id(self):
        response = self.client.get('/admin/suppliers/users?supplier_id=1000')

        assert response.status_code == 200

        self.data_api_client.get_supplier.assert_called_once_with('1000')
        self.data_api_client.find_users_iter.assert_called_once_with('1000')

    def test_should_have_supplier_name_on_page(self):
        response = self.client.get('/admin/suppliers/users?supplier_id=1000')

        assert response.status_code == 200
        assert "Supplier Name" in response.get_data(as_text=True)

    def test_should_indicate_if_there_are_no_users(self):
        self.data_api_client.find_users_iter.return_value = {}

        response = self.client.get('/admin/suppliers/users?supplier_id=1000')

        assert response.status_code == 200
        assert "This supplier has no users on the Digital Marketplace" in response.get_data(as_text=True)

    def test_should_show_user_details_on_page(self):

        response = self.client.get('/admin/suppliers/users?supplier_id=1000')

        assert response.status_code == 200
        assert "Test User" in response.get_data(as_text=True)
        assert "test.user@sme.com" in response.get_data(as_text=True)
        assert "09:33:53" in response.get_data(as_text=True)
        assert "23 July" in response.get_data(as_text=True)
        assert "12:46:01" in response.get_data(as_text=True)
        assert "29 June" in response.get_data(as_text=True)
        assert "No" in response.get_data(as_text=True)

        document = html.fromstring(response.get_data(as_text=True))
        assert document.xpath('//input[@value="Deactivate"][@type="submit"][@class="button-destructive"]')
        assert document.xpath('//form[@action="/admin/suppliers/users/999/deactivate"][@method="post"]')
        assert document.xpath('//button[@class="button-save"][contains(text(), "Move user to this supplier")]')
        assert document.xpath('//form[@action="/admin/suppliers/1234/move-existing-user"][@method="post"]')

    def test_should_show_unlock_button_if_user_locked(self):
        users = self.load_example_listing("users_response")
        users["users"][0]["locked"] = True
        self.data_api_client.find_users_iter.return_value = users['users']

        response = self.client.get('/admin/suppliers/users?supplier_id=1000')

        assert response.status_code == 200

        document = html.fromstring(response.get_data(as_text=True))
        assert document.xpath('//form[@action="/admin/suppliers/users/999/unlock"][@method="post"]')
        assert document.xpath('//input[@value="Unlock"][@type="submit"][@class="button-secondary"]')

    def test_should_show_activate_button_if_user_deactivated(self):
        users = self.load_example_listing("users_response")
        users["users"][0]["active"] = False
        self.data_api_client.find_users_iter.return_value = users['users']

        response = self.client.get('/admin/suppliers/users?supplier_id=1000')

        assert response.status_code == 200

        document = html.fromstring(response.get_data(as_text=True))
        assert document.xpath('//form[@action="/admin/suppliers/users/999/activate"][@method="post"]')
        assert document.xpath('//input[@value="Activate"][@type="submit"][@class="button-secondary"]')

    def test_should_call_api_to_unlock_user(self):
        self.data_api_client.update_user.return_value = self.load_example_listing("user_response")

        response = self.client.post('/admin/suppliers/users/999/unlock')

        self.data_api_client.update_user.assert_called_once_with(999, locked=False, updater="test@example.com")

        assert response.status_code == 302
        assert response.location == "http://localhost/admin/suppliers/users?supplier_id=1000"

    def test_should_call_api_to_activate_user(self):
        self.data_api_client.update_user.return_value = self.load_example_listing("user_response")

        response = self.client.post('/admin/suppliers/users/999/activate')

        self.data_api_client.update_user.assert_called_once_with(999, active=True, updater="test@example.com")

        assert response.status_code == 302
        assert response.location == "http://localhost/admin/suppliers/users?supplier_id=1000"

    def test_should_call_api_to_activate_user_and_redirect_to_source_if_present(self):
        self.data_api_client.update_user.return_value = self.load_example_listing("user_response")
        response = self.client.post(
            '/admin/suppliers/users/999/activate',
            data={'source': "http://example.com"}
        )

        self.data_api_client.update_user.assert_called_once_with(999, active=True, updater="test@example.com")

        assert response.status_code == 302
        assert response.location == "http://example.com"

    def test_should_call_api_to_deactivate_user(self):
        self.data_api_client.update_user.return_value = self.load_example_listing("user_response")
        response = self.client.post(
            '/admin/suppliers/users/999/deactivate',
            data={'supplier_id': 1000}
        )

        self.data_api_client.update_user.assert_called_once_with(999, active=False, updater="test@example.com")

        assert response.status_code == 302
        assert response.location == "http://localhost/admin/suppliers/users?supplier_id=1000"

    def test_should_call_api_to_deactivate_user_and_redirect_to_source_if_present(self):
        response = self.client.post(
            '/admin/suppliers/users/999/deactivate',
            data={'supplier_id': 1000, 'source': "http://example.com"}
        )

        self.data_api_client.update_user.assert_called_once_with(999, active=False, updater="test@example.com")

        assert response.status_code == 302
        assert response.location == "http://example.com"

    def test_should_call_api_to_move_user_to_another_supplier(self):
        self.data_api_client.get_user.return_value = self.load_example_listing("user_response")
        self.data_api_client.update_user.return_value = self.load_example_listing("user_response")

        response = self.client.post(
            '/admin/suppliers/1000/move-existing-user',
            data={'user_to_move_email_address': 'test.user@sme.com'}
        )

        self.data_api_client.update_user.assert_called_once_with(
            999, role='supplier', supplier_id=1000, active=True, updater="test@example.com"
        )

        assert response.status_code == 302
        assert response.location == "http://localhost/admin/suppliers/users?supplier_id=1000"


class TestSupplierServicesView(LoggedInApplicationTest):
    user_role = 'admin-ccs-category'

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.suppliers.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()

        self.data_api_client.get_supplier.return_value = self.load_example_listing("supplier_response")
        self.data_api_client.find_services.return_value = self.load_example_listing("services_response")
        self.data_api_client.find_frameworks.return_value = {
            'frameworks': [self.load_example_listing("framework_response")['frameworks']]
        }

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    @pytest.mark.parametrize("role, expected_code", [
        ("admin", 200),
        ("admin-ccs-category", 200),
        ("admin-ccs-sourcing", 403),
        ("admin-framework-manager", 200),
        ("admin-manager", 403),
    ])
    def test_supplier_services_accessible_to_users_with_right_roles(self, role, expected_code):
        self.user_role = role

        response = self.client.get('/admin/suppliers/1000/services')
        actual_code = response.status_code
        assert actual_code == expected_code, "Unexpected response {} for role {}".format(actual_code, role)

    @pytest.mark.parametrize("role, can_edit", [
        ("admin", False),
        ("admin-ccs-category", True),
        ("admin-framework-manager", False),
    ])
    def test_supplier_services_can_only_edit_users_with_right_roles(self, role, can_edit):
        self.user_role = role

        response = self.client.get('/admin/suppliers/1000/services')
        assert response.status_code == 200
        document = html.fromstring(response.get_data(as_text=True))
        remove_all_links = document.xpath('.//a[contains(text(), "Remove services")]')
        assert len(remove_all_links) == (1 if can_edit else 0)
        edit_service_links = document.xpath('.//a[contains(text(), "Edit")]')
        assert len(edit_service_links) == (1 if can_edit else 0)
        view_service_links = document.xpath('.//a[contains(text(), "View")]')
        assert len(view_service_links) == (0 if can_edit else 1)

    def test_should_404_if_supplier_does_not_exist_on_services(self):
        self.data_api_client.get_supplier.side_effect = HTTPError(Response(404))
        response = self.client.get('/admin/suppliers/999/services')
        assert response.status_code == 404

    def test_should_404_if_no_supplier_id_on_services(self):
        response = self.client.get('/admin/suppliers/services')
        assert response.status_code == 404

    def test_should_call_service_apis_with_supplier_id(self):
        response = self.client.get('/admin/suppliers/1000/services')

        assert response.status_code == 200

        self.data_api_client.get_supplier.assert_called_once_with(1000)
        self.data_api_client.find_services.assert_called_once_with(1000)

    def test_should_indicate_if_supplier_has_no_services(self):
        self.data_api_client.find_services.return_value = {'services': []}
        response = self.client.get('/admin/suppliers/1000/services')

        assert response.status_code == 200
        assert "This supplier has no services on the Digital Marketplace" in response.get_data(as_text=True)

    def test_should_have_supplier_name_on_services_page(self):
        self.data_api_client.find_services.return_value = {'services': []}

        response = self.client.get('/admin/suppliers/1000/services')

        assert response.status_code == 200
        assert "Supplier Name" in response.get_data(as_text=True)

    def test_should_show_service_details_on_page(self):
        response = self.client.get('/admin/suppliers/1000/services')

        assert response.status_code == 200
        assert "Contract Management" in response.get_data(as_text=True)
        assert '<a href="/g-cloud/services/5687123785023488">' in response.get_data(as_text=True)
        assert "5687123785023488" in response.get_data(as_text=True)
        assert "G-Cloud 8" in response.get_data(as_text=True)
        assert "Software as a Service" in response.get_data(as_text=True)
        assert "Public" in response.get_data(as_text=True)
        assert '<a href="/admin/services/5687123785023488">' in response.get_data(as_text=True)
        assert "Edit" in response.get_data(as_text=True)

    def test_should_show_correct_fields_for_disabled_service(self):
        service = self.load_example_listing("services_response")["services"][0]
        service["status"] = "disabled"
        self.data_api_client.find_services.return_value = {'services': [service]}

        response = self.client.get('/admin/suppliers/1000/services')

        assert response.status_code == 200
        assert "Removed" in response.get_data(as_text=True)
        assert "Edit" in response.get_data(as_text=True)

    def test_should_show_correct_fields_for_enabled_service(self):
        service = self.load_example_listing("services_response")["services"][0]
        service["status"] = "enabled"
        self.data_api_client.find_services.return_value = {'services': [service]}

        response = self.client.get('/admin/suppliers/1000/services')

        assert response.status_code == 200
        assert "Private" in response.get_data(as_text=True)
        assert "Edit" in response.get_data(as_text=True)

    def test_should_show_separate_tables_for_frameworks_if_supplier_has_service_on_framework(self):

        service_1 = self.load_example_listing("services_response")['services'][0]
        service_2 = service_1.copy()
        service_3 = service_1.copy()
        service_2['frameworkSlug'] = 'digital-outcomes-and-specialists-2'
        service_3['frameworkSlug'] = 'g-cloud-11'
        self.data_api_client.find_services.return_value = {'services': [service_1, service_2, service_3]}

        framework_1 = self.load_example_listing("framework_response")['frameworks']
        framework_2 = framework_1.copy()
        framework_3 = framework_1.copy()
        framework_2['slug'] = 'digital-outcomes-and-specialists-2'
        framework_2['id'] = 5
        framework_3['slug'] = 'g-cloud-11'
        framework_3['id'] = 22
        self.data_api_client.find_frameworks.return_value = {'frameworks': [framework_1, framework_2, framework_3]}

        response = self.client.get('/admin/suppliers/1000/services')

        assert response.status_code == 200

        response_data = response.get_data(as_text=True)
        assert 'g-cloud-11_services' in response_data
        assert 'g-cloud-8_services' in response_data
        assert 'digital-outcomes-and-specialists-2_services' in response_data

        gcloud8_table_index = response_data.find('g-cloud-8_services')
        dos_table_index = response_data.find('digital-outcomes-and-specialists-2_services')
        gcloud11_table_index = response_data.find('g-cloud-11_services')
        assert gcloud11_table_index < gcloud8_table_index < dos_table_index

    def test_remove_all_services_link_if_supplier_has_a_published_service_on_framework(self):
        service_1 = self.load_example_listing("services_response")["services"][0]
        service_2 = service_1.copy()
        service_2["status"] = "disabled"
        service_3 = service_1.copy()
        service_3["status"] = "enabled"

        self.data_api_client.find_services.return_value = {'services': [service_1, service_2, service_3]}

        response = self.client.get('/admin/suppliers/1000/services')
        assert response.status_code == 200

        document = html.fromstring(response.get_data(as_text=True))
        expected_link_text = "Remove services"
        expected_href = '/admin/suppliers/1234/services?remove=g-cloud-8'
        expected_link = document.xpath('.//a[contains(@href,"{}")]'.format(expected_href))[0]
        assert expected_link.text == expected_link_text

    @pytest.mark.parametrize('service_status', ['enabled', 'disabled', 'a_new_status'])
    def test_no_remove_all_services_link_if_supplier_service_not_published(self, service_status):
        service = self.load_example_listing('services_response')['services'][0]
        service["status"] = service_status

        self.data_api_client.find_services.return_value = {'services': [service]}

        response = self.client.get('/admin/suppliers/1000/services')
        assert response.status_code == 200

        document = html.fromstring(response.get_data(as_text=True))
        href = '/admin/suppliers/1234/services?remove=g-cloud-8'
        assert len(document.xpath('.//a[contains(@href,"{}")]'.format(href))) == 0


class TestSupplierServicesViewWithRemoveParam(LoggedInApplicationTest):
    user_role = 'admin-ccs-category'

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.suppliers.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()
        self.data_api_client.get_supplier.return_value = self.load_example_listing('supplier_response')
        self.data_api_client.find_services.return_value = self.load_example_listing('services_response')
        self.data_api_client.find_frameworks.return_value = {
            'frameworks': [self.load_example_listing("framework_response")['frameworks']]
        }

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    def test_400_if_supplier_has_no_services(self):
        framework = 'digital-outcomes-and-specialists-2'
        self.data_api_client.find_services.return_value = {'services': []}

        response = self.client.get('/admin/suppliers/1000/services?remove={}'.format(framework))

        assert response.status_code == 400

    def test_400_if_supplier_has_no_service_on_framework(self):
        framework = 'digital-outcomes-and-specialists-2'

        response = self.client.get('/admin/suppliers/1000/services?remove={}'.format(framework))

        assert response.status_code == 400

    @pytest.mark.parametrize('service_status', ['enabled', 'disabled', 'a_new_status'])
    def test_400_if_supplier_has_no_published_service_on_framework(self, service_status):
        framework = 'g-cloud-8'
        service = self.load_example_listing('services_response')['services'][0]
        service["status"] = service_status
        self.data_api_client.find_services.return_value = {'services': [service]}

        response = self.client.get('/admin/suppliers/1000/services?remove={}'.format(framework))

        assert response.status_code == 400

    def test_200_if_supplier_has_published_service_on_framework(self):
        framework = 'g-cloud-8'

        response = self.client.get('/admin/suppliers/1000/services?remove={}'.format(framework))

        assert response.status_code == 200

    def test_are_you_sure_banner_if_supplier_has_published_service_on_framework(self):
        framework = 'g-cloud-8'

        response = self.client.get('/admin/suppliers/1000/services?remove={}'.format(framework))
        assert response.status_code == 200

        document = html.fromstring(response.get_data(as_text=True))
        expected_banner_message = "Are you sure you want to remove Supplier Name's 'G-Cloud 8' services?"
        banner_message = document.xpath('//p[@class="banner-message"]//text()')[0].strip()
        assert banner_message == expected_banner_message


class TestDisableSupplierServicesView(LoggedInApplicationTest):
    user_role = 'admin-ccs-category'

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.suppliers.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()

        self.data_api_client.get_supplier.return_value = self.load_example_listing('supplier_response')
        self.data_api_client.find_services.return_value = self.load_example_listing('services_response')

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    @pytest.mark.parametrize('url_suffix', ['', '?remove=', '?foo=bar'])
    def test_400_if_no_framework_provided(self, url_suffix):

        response = self.client.post('/admin/suppliers/1000/services{}'.format(url_suffix))

        assert response.status_code == 400

    def test_400_if_supplier_has_no_service_on_framework(self):
        framework = 'g-cloud-8'
        self.data_api_client.find_services.return_value = {'services': []}

        response = self.client.post('/admin/suppliers/1000/services?remove={}'.format(framework))

        assert response.status_code == 400

    def test_disables_service(self):
        framework = 'g-cloud-8'

        response = self.client.post('/admin/suppliers/1000/services?remove={}'.format(framework))

        assert response.status_code == 302
        assert self.data_api_client.update_service_status.call_args_list == [mock.call(
            '5687123785023488', 'disabled', 'test@example.com'
        )]

    def test_disables_multiple_services(self):
        framework = 'g-cloud-8'
        service_1 = self.load_example_listing('services_response')['services'][0]
        service_2 = service_1.copy()
        service_2['id'] = '5687123785023489'
        service_3 = service_1.copy()
        service_3['id'] = '5687123785023490'

        self.data_api_client.find_services.return_value = {'services': [service_1, service_2, service_3]}

        response = self.client.post('/admin/suppliers/1000/services?remove={}'.format(framework))

        assert response.status_code == 302
        assert self.data_api_client.update_service_status.call_args_list == [
            mock.call('5687123785023488', 'disabled', 'test@example.com'),
            mock.call('5687123785023489', 'disabled', 'test@example.com'),
            mock.call('5687123785023490', 'disabled', 'test@example.com'),
        ]

    def test_flashes_success_message(self):
        framework = 'g-cloud-8'

        response = self.client.post('/admin/suppliers/1000/services?remove={}'.format(framework))

        assert response.status_code == 302

        expected_flash_message = "You removed all of PROACTIS Group Ltd's 'G-Cloud 8' services"
        with self.client.session_transaction() as session:
            assert session['_flashes'][0][1] == expected_flash_message


class TestSupplierInviteUserView(LoggedInApplicationTest):

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.suppliers.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()

        self.data_api_client.get_supplier.return_value = self.load_example_listing("supplier_response")
        self.data_api_client.find_users_iter.return_value = self.load_example_listing("users_response")['users']

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    def test_should_not_accept_bad_email_on_invite_user(self):
        response = self.client.post(
            "/admin/suppliers/1234/invite-user",
            data={'email_address': 'notatallvalid'},
            follow_redirects=True
        )

        assert response.status_code == 400
        assert "Please enter a valid email address" in response.get_data(as_text=True)

    def test_should_not_allow_missing_email_on_invite_user(self):
        response = self.client.post(
            "/admin/suppliers/1234/invite-user",
            data={},
            follow_redirects=True
        )

        assert response.status_code == 400
        assert "Email can not be empty" in response.get_data(as_text=True)

    def test_should_be_a_404_if_non_int_supplier_id(self):
        response = self.client.post(
            "/admin/suppliers/bad/invite-user",
            data={},
            follow_redirects=True
        )

        assert response.status_code == 404
        assert self.data_api_client.call_args_list == []

    def test_should_be_a_404_if_supplier_id_not_found(self):
        self.data_api_client.get_supplier.side_effect = HTTPError(Response(404))

        response = self.client.post(
            "/admin/suppliers/1234/invite-user",
            data={},
            follow_redirects=True
        )

        self.data_api_client.get_supplier.assert_called_once_with(1234)
        assert self.data_api_client.find_users_iter.call_args_list == []
        assert response.status_code == 404

    def test_should_be_a_404_if_supplier_users_not_found(self):
        self.data_api_client.find_users_iter.side_effect = HTTPError(Response(404))

        response = self.client.post(
            "/admin/suppliers/1234/invite-user",
            data={},
            follow_redirects=True
        )

        self.data_api_client.get_supplier.assert_called_once_with(1234)
        self.data_api_client.find_users_iter.assert_called_once_with(1234)
        assert response.status_code == 404

    @mock.patch('app.main.views.suppliers.send_user_account_email')
    def test_should_create_audit_event(self, send_user_account_email):

        res = self.client.post(
            '/admin/suppliers/1234/invite-user',
            data={
                'email_address': 'email@example.com'
            })

        self.data_api_client.create_audit_event.assert_called_once_with(
            audit_type=AuditTypes.invite_user,
            user='test@example.com',
            object_type='suppliers',
            object_id=1234,
            data={'invitedEmail': 'email@example.com'})

        assert res.status_code == 302
        assert res.location == 'http://localhost/admin/suppliers/users?supplier_id=1234'

    @mock.patch('app.main.views.suppliers.send_user_account_email')
    def test_should_not_send_email_if_bad_supplier_id(self, send_user_account_email):
        self.data_api_client.get_supplier.side_effect = HTTPError(Response(404))
        self.data_api_client.find_users_iter.side_effect = HTTPError(Response(404))

        res = self.client.post(
            "/admin/suppliers/1234/invite-user",
            data={
                'email_address': 'this@isvalid.com',
            })

        assert self.data_api_client.find_users_iter.call_args_list == []
        assert send_user_account_email.call_args_list == []
        assert res.status_code == 404

    @mock.patch('app.main.views.suppliers.send_user_account_email')
    def test_should_call_send_email_with_correct_params(self, send_user_account_email):
        with self.app.app_context():
            res = self.client.post(
                "/admin/suppliers/1234/invite-user",
                data={
                    'email_address': 'this@isvalid.com',
                }
            )

            send_user_account_email.assert_called_once_with(
                'supplier',
                'this@isvalid.com',
                current_app.config['NOTIFY_TEMPLATES']['invite_contributor'],
                extra_token_data={
                    'supplier_id': 1234,
                    'supplier_name': 'Supplier Name'
                },
                personalisation={
                    'user': 'The Digital Marketplace team',
                    'supplier': 'Supplier Name'
                }
            )

            assert res.status_code == 302
            assert res.location == 'http://localhost/admin/suppliers/users?supplier_id=1234'

    @mock.patch('app.main.views.suppliers.send_user_account_email')
    def test_should_strip_whitespace_surrounding_invite_user_email_address_field(self, send_user_account_email):
        with self.app.app_context():
            self.client.post(
                "/admin/suppliers/1234/invite-user",
                data={
                    'email_address': '  this@isvalid.com  ',
                }
            )

            send_user_account_email.assert_called_once_with(
                'supplier',
                'this@isvalid.com',
                current_app.config['NOTIFY_TEMPLATES']['invite_contributor'],
                extra_token_data={
                    'supplier_id': 1234,
                    'supplier_name': 'Supplier Name'
                },
                personalisation={
                    'user': 'The Digital Marketplace team',
                    'supplier': 'Supplier Name'
                }
            )

    @mock.patch('dmutils.email.user_account_email.DMNotifyClient')
    def test_should_be_a_503_if_email_fails(self, DMNotifyClient):
        notify_client_mock = mock.Mock()
        notify_client_mock.send_email.side_effect = EmailError("Arrrgh")
        DMNotifyClient.return_value = notify_client_mock

        res = self.client.post(
            "/admin/suppliers/1234/invite-user",
            data={
                'email_address': 'this@isvalid.com',
            })

        assert res.status_code == 503


class TestUpdatingSupplierName(LoggedInApplicationTest):

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.suppliers.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    @pytest.mark.parametrize("allowed_role", ["admin", "admin-ccs-category"])
    def test_admin_and_ccs_category_roles_can_update_supplier_name(self, allowed_role):
        self.user_role = allowed_role
        self.data_api_client.get_supplier.return_value = {"suppliers": {"id": 1234, "name": "Something Old"}}
        response = self.client.post(
            '/admin/suppliers/1234/edit/name',
            data={'new_supplier_name': 'Something New'}
        )
        assert response.status_code == 302
        assert response.location == 'http://localhost/admin/suppliers?supplier_id=1234'
        self.data_api_client.update_supplier.assert_called_once_with(
            1234, {'name': "Something New"}, "test@example.com"
        )

    def test_ccs_sourcing_role_can_not_update_supplier_name(self):
        self.user_role = 'admin-ccs-sourcing'
        response = self.client.post(
            '/admin/suppliers/1234/edit/name',
            data={'new_supplier_name': 'Something New'}
        )
        assert response.status_code == 403
        assert self.data_api_client.update_supplier.call_args_list == []


class TestViewingASupplierDeclaration(LoggedInApplicationTest):
    user_role = 'admin-ccs-sourcing'

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.suppliers.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()

        self.data_api_client.get_supplier.return_value = self.load_example_listing('supplier_response')
        self.data_api_client.get_framework.return_value = self.load_example_listing('framework_response')
        self.data_api_client.get_supplier_declaration.return_value = self.load_example_listing('declaration_response')

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    def test_should_not_be_visible_to_admin_users(self):
        self.user_role = 'admin'

        response = self.client.get('/admin/suppliers/1234/edit/declarations/g-cloud-7')

        assert response.status_code == 403

    def test_should_404_if_supplier_does_not_exist(self):
        self.data_api_client.get_supplier.side_effect = APIError(Response(404))

        response = self.client.get('/admin/suppliers/1234/edit/declarations/g-cloud-7')

        assert response.status_code == 404
        self.data_api_client.get_supplier.assert_called_once_with('1234')
        assert self.data_api_client.get_framework.call_args_list == []

    def test_should_404_if_framework_does_not_exist(self):
        self.data_api_client.get_framework.side_effect = APIError(Response(404))

        response = self.client.get('/admin/suppliers/1234/edit/declarations/g-cloud-7')

        assert response.status_code == 404
        self.data_api_client.get_supplier.assert_called_with('1234')
        self.data_api_client.get_framework.assert_called_with('g-cloud-7')

    def test_should_not_404_if_declaration_does_not_exist(self):
        self.data_api_client.get_supplier_declaration.side_effect = APIError(Response(404))

        response = self.client.get('/admin/suppliers/1234/edit/declarations/g-cloud-7')

        assert response.status_code == 200
        self.data_api_client.get_supplier.assert_called_once_with('1234')
        self.data_api_client.get_framework.assert_called_once_with('g-cloud-7')
        self.data_api_client.get_supplier_declaration.assert_called_once_with('1234', 'g-cloud-7')

    def test_should_show_declaration(self):
        response = self.client.get('/admin/suppliers/1234/edit/declarations/g-cloud-7')
        document = html.fromstring(response.get_data(as_text=True))

        assert response.status_code == 200
        data = document.cssselect('.summary-item-row td.summary-item-field')
        assert data[0].text_content().strip() == "Yes"

    def test_should_show_dos_declaration(self):
        response = self.client.get('/admin/suppliers/1234/edit/declarations/digital-outcomes-and-specialists')
        document = html.fromstring(response.get_data(as_text=True))

        assert response.status_code == 200
        data = document.cssselect('.summary-item-row td.summary-item-field')
        assert data[0].text_content().strip() == "Yes"

    def test_should_403_if_framework_is_open(self):
        self.data_api_client.get_framework.return_value['frameworks']['status'] = 'open'

        response = self.client.get('/admin/suppliers/1234/edit/declarations/digital-outcomes-and-specialists')
        assert response.status_code == 403


class TestEditingASupplierDeclaration(LoggedInApplicationTest):
    user_role = 'admin-ccs-sourcing'

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.suppliers.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()
        self.data_api_client.get_supplier.return_value = self.load_example_listing('supplier_response')
        self.data_api_client.get_framework.return_value = self.load_example_listing('framework_response')
        self.data_api_client.get_supplier_declaration.return_value = self.load_example_listing('declaration_response')

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    def test_should_not_be_visible_to_admin_users(self):
        self.user_role = 'admin'

        response = self.client.get('/admin/suppliers/1234/edit/declarations/g-cloud-7/section')

        assert response.status_code == 403

    def test_should_404_if_supplier_does_not_exist(self):
        self.data_api_client.get_supplier.side_effect = APIError(Response(404))

        response = self.client.get('/admin/suppliers/1234/edit/declarations/g-cloud-7/g-cloud-7-essentials')

        assert response.status_code == 404
        self.data_api_client.get_supplier.assert_called_once_with('1234')
        assert self.data_api_client.get_framework.call_args_list == []

    def test_should_404_if_framework_does_not_exist(self):
        self.data_api_client.get_framework.side_effect = APIError(Response(404))

        response = self.client.get('/admin/suppliers/1234/edit/declarations/g-cloud-7/g-cloud-7-essentials')

        assert response.status_code == 404
        self.data_api_client.get_supplier.assert_called_once_with('1234')
        self.data_api_client.get_framework.assert_called_once_with('g-cloud-7')

    def test_should_404_if_section_does_not_exist(self):
        self.data_api_client.get_supplier_declaration.side_effect = APIError(Response(404))

        response = self.client.get('/admin/suppliers/1234/edit/declarations/g-cloud-7/not_a_section')

        assert response.status_code == 404

    def test_should_not_404_if_declaration_does_not_exist(self):
        self.data_api_client.get_supplier_declaration.side_effect = APIError(Response(404))

        response = self.client.get('/admin/suppliers/1234/edit/declarations/g-cloud-7/g-cloud-7-essentials')

        assert response.status_code == 200
        self.data_api_client.get_supplier.assert_called_once_with('1234')
        self.data_api_client.get_framework.assert_called_once_with('g-cloud-7')
        self.data_api_client.get_supplier_declaration.assert_called_once_with('1234', 'g-cloud-7')

    def test_should_prefill_form_with_declaration(self):
        response = self.client.get('/admin/suppliers/1234/edit/declarations/g-cloud-7/g-cloud-7-essentials')
        document = html.fromstring(response.get_data(as_text=True))

        assert response.status_code == 200
        assert document.cssselect('#input-PR1-1')[0].checked
        assert not document.cssselect('#input-PR1-2')[0].checked

    def test_should_set_declaration(self):
        self.client.post(
            '/admin/suppliers/1234/edit/declarations/g-cloud-7/g-cloud-7-essentials',
            data={'PR1': 'false'})

        declaration = self.load_example_listing('declaration_response')['declaration']
        declaration['PR1'] = False
        declaration['SQ1-3'] = None
        declaration['SQC3'] = None

        self.data_api_client.set_supplier_declaration.assert_called_once_with(
            '1234', 'g-cloud-7', declaration, 'test@example.com')


@mock.patch('app.main.views.suppliers.download_agreement_file')
class TestDownloadSignedAgreementFile(LoggedInApplicationTest):
    user_role = 'admin-ccs-sourcing'

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.suppliers.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    def test_download_agreement_is_called_with_the_right_parameters(self, download_agreement_file):
        self.data_api_client.get_supplier_framework_info.return_value = {
            'frameworkInterest': {'agreementPath': '/path/to/file/in/s3/1234-signed-agreement-file.pdf'}
        }
        # Mock out a response from download_agreement_file() - we don't care what it is
        download_agreement_file.side_effect = HTTPError(Response(404))
        self.client.get('/admin/suppliers/1234/agreement/g-cloud-7')
        download_agreement_file.assert_called_once_with('1234', 'g-cloud-7', 'signed-agreement-file.pdf')


@mock.patch('app.main.views.suppliers.s3')
class TestDownloadAgreementFile(LoggedInApplicationTest):
    user_role = 'admin-ccs-sourcing'

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.suppliers.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()

        self.data_api_client.get_supplier_framework_info.return_value = {
            'frameworkInterest': {'declaration': {'key': 'Supplier name'}}
        }

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    @pytest.mark.parametrize("role, expected_code", [
        ("admin", 403),
        ("admin-ccs-category", 302),
        ("admin-ccs-sourcing", 302),
        ("admin-framework-manager", 302),
        ("admin-manager", 403),
    ])
    def test_download_agreement_file_accessible_to_specific_user_roles(self, s3, role, expected_code):
        self.user_role = role
        s3.S3.return_value.get_signed_url.return_value = 'http://foo/blah?extra'

        response = self.client.get('/admin/suppliers/1234/agreements/g-cloud-7/foo.pdf')
        actual_code = response.status_code
        assert actual_code == expected_code, "Unexpected response {} for role {}".format(actual_code, role)

    def test_should_404_if_no_supplier_framework_declaration(self, s3):
        self.data_api_client.get_supplier_framework_info.return_value = {
            'frameworkInterest': {'declaration': None}
        }
        response = self.client.get('/admin/suppliers/1234/agreements/g-cloud-7/foo.pdf')
        assert response.status_code == 404

    def test_should_404_if_document_does_not_exist(self, s3):
        self.data_api_client.get_supplier_framework_info.return_value = {
            'frameworkInterest': {'declaration': {'SQ1-1a': 'Supplier name'}}
        }
        s3.S3.return_value.get_signed_url.return_value = None

        response = self.client.get('/admin/suppliers/1234/agreements/g-cloud-7/foo.pdf')

        s3.S3.return_value.get_signed_url.assert_called_once_with('g-cloud-7/agreements/1234/1234-foo.pdf')
        assert response.status_code == 404

    def test_should_redirect(self, s3):
        s3.S3.return_value.get_signed_url.return_value = 'http://foo/blah?extra'

        self.app.config['DM_ASSETS_URL'] = 'https://example'

        response = self.client.get('/admin/suppliers/1234/agreements/g-cloud-7/foo.pdf')

        s3.S3.return_value.get_signed_url.assert_called_once_with('g-cloud-7/agreements/1234/1234-foo.pdf')
        assert response.status_code == 302
        assert response.location == 'https://example/blah?extra'

    def test_admin_should_be_able_to_download_countersigned_agreement(self, s3):
        s3.S3.return_value.get_signed_url.return_value = 'http://foo/blah?extra'
        self.app.config['DM_ASSETS_URL'] = 'https://example'

        response = self.client.get(
            '/admin/suppliers/1234/agreements/g-cloud-7/countersigned-framework-agreement.pdf'
        )

        s3.S3.return_value.get_signed_url.assert_called_once_with(
            'g-cloud-7/agreements/1234/1234-countersigned-framework-agreement.pdf'
        )
        assert response.status_code == 302


@mock.patch('app.main.views.suppliers.s3')
class TestListCountersignedAgreementFile(LoggedInApplicationTest):
    user_role = 'admin-ccs-sourcing'

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.suppliers.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    def test_should_not_be_visible_to_admin_users(self, s3):
        self.user_role = 'admin'

        response = self.client.get('/admin/suppliers/1234/countersigned-agreements/g-cloud-7')

        assert response.status_code == 403

    def test_should_be_visible_to_admin_sourcing_users(self, s3):
        s3.S3.return_value.get_key.return_value = {
            'size': '7050',
            'path': u'g-cloud-7/agreements/93495/93495-countersigned-framework-agreement.pdf',
            'ext': u'pdf',
            'last_modified': u'2016-01-15T12:58:08.000000Z',
            'filename': u'93495-countersigned-framework-agreement'
        }
        self.data_api_client.get_supplier_framework_info.return_value = \
            {"frameworkInterest": {
                "onFramework": True,
                "agreementStatus": "signed",
                "countersignedPath": "g-cloud-7/agreements/93495/93495-countersigned-framework-agreement.pdf"
            }}

        response = self.client.get('/admin/suppliers/1234/countersigned-agreements/g-cloud-7')
        assert response.status_code == 200

    def test_should_display_no_documents_if_no_documents_listed(self, s3):
        s3.S3.return_value.get_key.return_value = []
        self.data_api_client.get_supplier_framework_info.return_value = {
            "frameworkInterest": {
                "onFramework": True,
                "agreementStatus": "signed",
                "countersignedPath": None
            }
        }

        response = self.client.get('/admin/suppliers/1234/countersigned-agreements/g-cloud-7')
        assert 'No agreements have been uploaded' in response.get_data(as_text=True)

    @pytest.mark.parametrize(
        'confirmation_param_value,confirmation_message_shown',
        [('true', True), ('false', False), (0, False), ('', False)]
    )
    def test_remove_countersigned_agreement_confirmation_flag(
            self, s3, confirmation_param_value, confirmation_message_shown
    ):
        s3.S3.return_value.get_key.return_value = {
            'size': '7050',
            'path': u'g-cloud-7/agreements/93495/93495-countersigned-framework-agreement.pdf',
            'ext': u'pdf',
            'last_modified': u'2016-01-15T12:58:08.000000Z',
            'filename': u'93495-countersigned-framework-agreement'
        }
        self.data_api_client.get_supplier_framework_info.return_value = \
            {"frameworkInterest": {
                "onFramework": True,
                "agreementStatus": "signed",
                "countersignedPath": "g-cloud-7/agreements/93495/93495-countersigned-framework-agreement.pdf"
            }}

        response = self.client.get(
            '/admin/suppliers/1234/countersigned-agreements/g-cloud-7?remove_countersigned_agreement={}'.format(
                confirmation_param_value
            )
        )

        assert ('Do you want to remove the countersigned agreement?' in response.get_data(as_text=True)) == \
            confirmation_message_shown


@freeze_time('2016-12-25 06:30:01')
@mock.patch('app.main.views.suppliers.s3')
class TestUploadCountersignedAgreementFile(LoggedInApplicationTest):
    user_role = 'admin-ccs-sourcing'

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.suppliers.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    def test_countersigned_agreement_displays_error_for_wrong_format(self, s3):
        s3.S3.return_value.get_key.return_value = {
            'size': '7050',
            'path': u'g-cloud-7/agreements/93495/93495-countersigned-framework-agreement.pdf',
            'ext': u'pdf',
            'last_modified': u'2016-01-15T12:58:08.000000Z',
            'filename': u'93495-countersigned-framework-agreement'
        }
        self.data_api_client.get_supplier_framework_info.return_value = \
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

        assert 'This must be a pdf' in response.get_data(as_text=True)
        assert response.status_code == 200

    def test_can_upload_countersigned_agreement_for_signed_agreement(self, s3):
        expected_countersign_path = 'g-cloud-7/agreements/1234/1234-agreement-countersignature-2016-12-25-063001.pdf'
        s3.S3.return_value.get_key.return_value = {
            'size': '7050',
            'path': u'g-cloud-7/agreements/1234/1234-countersigned-framework-agreement.pdf',
            'ext': u'pdf',
            'last_modified': u'2016-01-15T12:58:08.000000Z',
            'filename': u'1234-countersigned-framework-agreement'
        }
        self.data_api_client.get_supplier_framework_info.return_value = {
            "frameworkInterest": {
                "onFramework": True,
                "agreementStatus": "signed",
                "agreementId": 1212,
                "countersignedPath": None,
                "declaration": {"nameOfOrganisation": "Supplier Mc Supply Face"},
            }
        }
        response = self.client.post(
            '/admin/suppliers/1234/countersigned-agreements/g-cloud-7',
            data={'countersigned_agreement': (BytesIO(b"this is a test"), 'countersigned_agreement.pdf')}
        )

        self.data_api_client.approve_agreement_for_countersignature.assert_called_once_with(
            1212,
            'test@example.com',
            '1234'
        )

        s3.S3.return_value.save.assert_called_once_with(
            expected_countersign_path,
            mock.ANY,
            acl='bucket-owner-full-control',
            move_prefix=None,
            download_filename='Supplier_Mc_Supply_Face-1234-agreement-countersignature.pdf'
        )

        self.data_api_client.update_framework_agreement.assert_called_once_with(
            1212,
            {"countersignedAgreementPath": expected_countersign_path},
            'test@example.com'
        )

        self.data_api_client.create_audit_event.assert_called_once_with(
            audit_type=AuditTypes.upload_countersigned_agreement,
            user='test@example.com',
            object_type='suppliers',
            object_id=u'1234',
            data={'upload_countersigned_agreement': expected_countersign_path}
        )

        assert response.status_code == 302
        assert response.location == 'http://localhost/admin/suppliers/1234/countersigned-agreements/g-cloud-7'

    def test_can_upload_countersigned_agreement_for_already_countersigned_agreement(self, s3):
        s3.S3.return_value.get_key.return_value = {
            'size': '7050',
            'path': u'g-cloud-7/agreements/1234/1234-countersigned-framework-agreement.pdf',
            'ext': u'pdf',
            'last_modified': u'2016-01-15T12:58:08.000000Z',
            'filename': u'1234-countersigned-framework-agreement'
        }
        self.data_api_client.get_supplier_framework_info.return_value = \
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

        assert self.data_api_client.approve_agreement_for_countersignature.call_args_list == []

        s3.S3.return_value.save.assert_called_once_with(
            "g-cloud-7/agreements/1234/1234-agreement-countersignature-2016-12-25-063001.pdf",
            mock.ANY,
            acl='bucket-owner-full-control',
            move_prefix=None,
            download_filename='Supplier_Mc_Supply_Face-1234-agreement-countersignature.pdf'
        )

        self.data_api_client.update_framework_agreement.assert_called_once_with(
            1212,
            {"countersignedAgreementPath": "g-cloud-7/agreements/1234/1234-agreement-countersignature-2016-12-25-063001.pdf"},  # noqa
            'test@example.com'
        )

        self.data_api_client.create_audit_event.assert_called_once_with(
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

    def test_can_upload_countersigned_agreement_for_framework_without_declaration(self, s3):
        s3.S3.return_value.get_key.return_value = {
            'size': '7050',
            'path': u'g-cloud-7/agreements/1234/1234-countersigned-framework-agreement.pdf',
            'ext': u'pdf',
            'last_modified': u'2016-01-15T12:58:08.000000Z',
            'filename': u'1234-countersigned-framework-agreement'
        }
        self.data_api_client.get_supplier_framework_info.return_value = \
            {"frameworkInterest": {
                "onFramework": True,
                "agreementStatus": "signed",
                "agreementId": 1212,
                "countersignedPath": None
            }}
        self.data_api_client.get_supplier.return_value = \
            {"suppliers": {
                "name": "DM Supplier Name"
            }}
        response = self.client.post('/admin/suppliers/1234/countersigned-agreements/g-cloud-7',
                                    data=dict(
                                        countersigned_agreement=(BytesIO(b"this is a test"),
                                                                 'countersigned_agreement.pdf'),
                                    ))

        self.data_api_client.approve_agreement_for_countersignature.assert_called_once_with(
            1212,
            'test@example.com',
            '1234'
        )

        s3.S3.return_value.save.assert_called_once_with(
            "g-cloud-7/agreements/1234/1234-agreement-countersignature-2016-12-25-063001.pdf",
            mock.ANY,
            acl='bucket-owner-full-control',
            move_prefix=None,
            download_filename='DM_Supplier_Name-1234-agreement-countersignature.pdf'
        )

        self.data_api_client.update_framework_agreement.assert_called_once_with(
            1212,
            {
                "countersignedAgreementPath": "g-cloud-7/agreements/1234/1234-agreement-countersignature-2016-12-25-063001.pdf"},  # noqa
            'test@example.com'
        )

        assert response.status_code == 302
        assert response.location == 'http://localhost/admin/suppliers/1234/countersigned-agreements/g-cloud-7'
        self.data_api_client.create_audit_event.assert_called_once_with(
            audit_type=AuditTypes.upload_countersigned_agreement,
            user='test@example.com',
            object_type='suppliers',
            object_id=u'1234',
            data={
                'upload_countersigned_agreement':
                    'g-cloud-7/agreements/1234/1234-agreement-countersignature-2016-12-25-063001.pdf'
            }
        )


@mock.patch('app.main.views.suppliers.s3')
class TestRemoveCountersignedAgreementFile(LoggedInApplicationTest):
    user_role = 'admin-ccs-sourcing'

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.suppliers.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    def test_should_remove_countersigned_agreement(self, s3):
        s3.S3.return_value.delete_key.return_value = {'Key': 'digitalmarketplace-documents-dev-dev'
                                                      ',g-cloud-7/agreements/93495/93495-'
                                                      'countersigned-framework-agreement.pdf'}
        response = self.client.post('/admin/suppliers/1234/countersigned-agreements-remove/g-cloud-7')
        assert response.status_code == 302

    def test_admin_should_not_be_able_to_remove_countersigned_agreement(self, s3):
        self.user_role = 'admin'
        s3.S3.return_value.delete_key.return_value = {'Key': 'digitalmarketplace-documents-dev-dev'
                                                      ',g-cloud-7/agreements/93495/93495-'
                                                      'countersigned-framework-agreement.pdf'}
        response = self.client.post('/admin/suppliers/1234/countersigned-agreements-remove/g-cloud-7')
        assert response.status_code == 403

    def test_should_display_remove_countersigned_agreement_message(self, s3):
        s3.S3.return_value.get_key.return_value = {
            'size': '7050',
            'path': u'g-cloud-7/agreements/93495/93495-countersigned-framework-agreement.pdf',
            'ext': u'pdf',
            'last_modified': u'2016-01-15T12:58:08.000000Z',
            'filename': u'93495-countersigned-framework-agreement'
        }
        self.data_api_client.get_supplier_framework_info.return_value = \
            {"frameworkInterest": {
                "onFramework": True,
                "agreementStatus": "signed",
                "countersignedPath": "g-cloud-7/agreements/93495/93495-countersigned-framework-agreement.pdf"
            }}
        response = self.client.get('/admin/suppliers/1234/countersigned-agreements-remove/g-cloud-7',
                                   follow_redirects=True)
        assert 'Do you want to remove the countersigned agreement?' in response.get_data(as_text=True)
        assert response.status_code == 200


@mock.patch('app.main.views.suppliers.s3')
class TestViewingSignedAgreement(LoggedInApplicationTest):
    user_role = 'admin-ccs-sourcing'

    services_response = (
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
    )

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.suppliers.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()
        self.data_api_client.get_supplier.return_value = self.load_example_listing('supplier_response')
        self.data_api_client.get_framework.return_value = self.load_example_listing('framework_response')
        self.data_api_client.get_supplier_framework_info.return_value = self.load_example_listing(
            'supplier_framework_response'
        )

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    def test_should_404_if_supplier_does_not_exist(self, s3):
        self.data_api_client.get_supplier.side_effect = APIError(Response(404))

        response = self.client.get('/admin/suppliers/1234/agreements/g-cloud-8')

        assert response.status_code == 404
        self.data_api_client.get_supplier.assert_called_with('1234')
        assert self.data_api_client.get_framework.call_args_list == []

    def test_should_404_if_framework_does_not_exist(self, s3):
        self.data_api_client.get_framework.side_effect = APIError(Response(404))

        response = self.client.get('/admin/suppliers/1234/agreements/g-cloud-8')

        assert response.status_code == 404
        self.data_api_client.get_supplier.assert_called_once_with('1234')
        self.data_api_client.get_framework.assert_called_once_with('g-cloud-8')

    def test_should_404_if_agreement_not_returned(self, s3):
        not_returned = self.load_example_listing('supplier_framework_response')
        not_returned['frameworkInterest']['agreementReturned'] = False
        self.data_api_client.get_supplier_framework_info.return_value = not_returned
        response = self.client.get('/admin/suppliers/1234/agreements/g-cloud-8')

        assert response.status_code == 404
        self.data_api_client.get_supplier.assert_called_once_with('1234')
        self.data_api_client.get_framework.assert_called_once_with('g-cloud-8')
        self.data_api_client.get_supplier_framework_info.assert_called_once_with('1234', 'g-cloud-8')

    def test_should_404_if_agreement_has_no_version(self, s3):
        self.data_api_client.get_framework.return_value = {'frameworks': {}}
        response = self.client.get('/admin/suppliers/1234/agreements/g-cloud-8')

        assert response.status_code == 404
        self.data_api_client.get_supplier.assert_called_once_with('1234')
        self.data_api_client.get_framework.assert_called_once_with('g-cloud-8')

    def test_should_show_agreement_details_on_page(self, s3):
        self.data_api_client.find_services_iter.return_value = iter(self.services_response)

        with mock.patch('app.main.views.suppliers.get_signed_url') as mock_get_url:
            mock_get_url.return_value = "http://example.com/document/1234.pdf"

            response = self.client.get('/admin/suppliers/1234/agreements/g-cloud-8')
            document = html.fromstring(response.get_data(as_text=True))
            assert response.status_code == 200
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

    def test_should_404_if_no_signed_url(self, s3):
        with mock.patch('app.main.views.suppliers.get_signed_url') as mock_get_url:
            mock_get_url.return_value = None
            response = self.client.get('/admin/suppliers/1234/agreements/g-cloud-8')
            assert response.status_code == 404

    def test_should_embed_for_pdf_file(self, s3):
        with mock.patch('app.main.views.suppliers.get_signed_url') as mock_get_url:
            mock_get_url.return_value = "http://example.com/document/1234.pdf"
            response = self.client.get('/admin/suppliers/1234/agreements/g-cloud-8')
            document = html.fromstring(response.get_data(as_text=True))
            assert response.status_code == 200
            assert len(document.xpath('//embed[@src="http://example.com/document/1234.pdf"]')) == 1
            assert len(document.xpath('//img[@src="http://example.com/document/1234.pdf"]')) == 0

    def test_should_img_for_image_file(self, s3):
        supplier_framework_info = self.load_example_listing(
            'supplier_framework_response'
        )
        supplier_framework_info['frameworkInterest']['agreementPath'] = 'path/to/img.jpg'
        self.data_api_client.get_supplier_framework_info.return_value = supplier_framework_info

        with mock.patch('app.main.views.suppliers.get_signed_url') as mock_get_url:
            mock_get_url.return_value = "http://example.com/document/1234.png"
            response = self.client.get('/admin/suppliers/1234/agreements/g-cloud-8')
            document = html.fromstring(response.get_data(as_text=True))
            assert response.status_code == 200
            assert len(document.xpath('//img[@src="http://example.com/document/1234.png"]')) == 1
            assert len(document.xpath('//embed[@src="http://example.com/document/1234.png"]')) == 0

    @pytest.mark.parametrize("role, expected_code", [
        ("admin", 403),
        ("admin-ccs-category", 200),
        ("admin-ccs-sourcing", 200),
        ("admin-framework-manager", 200),
        ("admin-manager", 403),
    ])
    def test_view_signed_agreement_accessible_to_specific_user_roles(self, s3, role, expected_code):
        self.user_role = role

        with mock.patch('app.main.views.suppliers.get_signed_url') as mock_get_url:
            mock_get_url.return_value = "http://example.com/document/1234.pdf"

            response = self.client.get('/admin/suppliers/1234/agreements/g-cloud-8')
            actual_code = response.status_code
            assert actual_code == expected_code, "Unexpected response {} for role {}".format(actual_code, role)


class TestPutSignedAgreementOnHold(LoggedInApplicationTest):
    user_role = 'admin-ccs-sourcing'

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.suppliers.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()
        self.data_api_client.put_signed_agreement_on_hold.return_value = self.put_signed_agreement_on_hold_return_value

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

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

    def test_it_fails_if_not_ccs_admin(self):
        self.user_role = 'admin'

        res = self.client.post('/admin/suppliers/agreements/123/on-hold', data={"nameOfOrganisation": "Test"})

        assert self.data_api_client.put_signed_agreement_on_hold.call_args_list == []
        assert res.status_code == 403

    def test_happy_path(self):
        res = self.client.post(
            "/admin/suppliers/agreements/123/on-hold",
            data={"nameOfOrganisation": "Test"},
        )

        self.data_api_client.put_signed_agreement_on_hold.assert_called_once_with('123', 'test@example.com')
        self.assert_flashes("The agreement for Test was put on hold.")
        assert res.status_code == 302

        parsed_location = urlparse(res.location)
        assert parsed_location.path == "/admin/suppliers/4321/agreements/g-cloud-99-flake/next"
        assert parse_qs(parsed_location.query) == {}

    def test_happy_path_with_next_status(self):
        res = self.client.post(
            "/admin/suppliers/agreements/123/on-hold?next_status=on-hold",
            data={"nameOfOrganisation": "Test"},
        )

        self.data_api_client.put_signed_agreement_on_hold.assert_called_once_with('123', 'test@example.com')
        self.assert_flashes("The agreement for Test was put on hold.")
        assert res.status_code == 302

        parsed_location = urlparse(res.location)
        assert parsed_location.path == "/admin/suppliers/4321/agreements/g-cloud-99-flake/next"
        assert parse_qs(parsed_location.query) == {"status": ["on-hold"]}


class TestApproveAgreement(LoggedInApplicationTest):
    user_role = 'admin-ccs-sourcing'

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.suppliers.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()
        self.data_api_client.approve_agreement_for_countersignature.return_value = {
            "agreement": {
                "id": 123,
                "supplierId": 4321,
                "frameworkSlug": "g-cloud-99p-world",
            },
        }

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    def test_it_fails_if_not_ccs_admin(self):
        self.user_role = 'admin'
        res = self.client.post('/admin/suppliers/agreements/123/approve', data={"nameOfOrganisation": "Test"})

        assert self.data_api_client.approve_agreement_for_countersignature.call_args_list == []
        assert res.status_code == 403

    def test_happy_path(self):
        res = self.client.post(
            "/admin/suppliers/agreements/123/approve",
            data={"nameOfOrganisation": "Test"},
        )

        self.data_api_client.approve_agreement_for_countersignature.assert_called_once_with(
            '123', 'test@example.com', '1234'
        )
        self.assert_flashes("The agreement for Test was approved. They will receive a countersigned version soon.")
        assert res.status_code == 302

        parsed_location = urlparse(res.location)
        assert parsed_location.path == "/admin/suppliers/4321/agreements/g-cloud-99p-world/next"
        assert parse_qs(parsed_location.query) == {}

    def test_happy_path_with_next_status_and_unicode_supplier_name(self):
        res = self.client.post(
            "/admin/suppliers/agreements/123/approve?next_status=on-hold",
            data={"nameOfOrganisation": u"Test O\u2019Connor"},
        )

        self.data_api_client.approve_agreement_for_countersignature.assert_called_once_with(
            '123', 'test@example.com', '1234'
        )
        self.assert_flashes(u"The agreement for Test O\u2019Connor was approved. They will receive a countersigned "
                            "version soon.")
        assert res.status_code == 302

        parsed_location = urlparse(res.location)
        assert parsed_location.path == "/admin/suppliers/4321/agreements/g-cloud-99p-world/next"
        assert parse_qs(parsed_location.query) == {"status": ["on-hold"]}


class TestUnapproveAgreement(LoggedInApplicationTest):
    user_role = 'admin-ccs-sourcing'

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.suppliers.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()
        self.data_api_client.unapprove_agreement_for_countersignature.return_value = {
            "agreement": {
                "id": 123,
                "supplierId": 4321,
                "frameworkSlug": "g-cloud-99p-world",
            },
        }

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    def test_it_fails_if_not_ccs_admin(self):
        self.user_role = 'admin'

        res = self.client.post('/admin/suppliers/agreements/123/unapprove', data={"nameOfOrganisation": "Test"})

        assert self.data_api_client.unapprove_agreement_for_countersignature.call_args_list == []
        assert res.status_code == 403

    def test_happy_path(self):
        res = self.client.post(
            "/admin/suppliers/agreements/123/unapprove",
            data={"nameOfOrganisation": "Test"},
        )

        self.data_api_client.unapprove_agreement_for_countersignature.assert_called_once_with(
            '123',
            'test@example.com',
            '1234',
        )
        self.assert_flashes("The agreement for Test had its approval cancelled. You can approve it again at any time.")
        assert res.status_code == 302

        parsed_location = urlparse(res.location)
        assert parsed_location.path == "/admin/suppliers/4321/agreements/g-cloud-99p-world"
        assert parse_qs(parsed_location.query) == {}

    def test_happy_path_with_next_status_and_unicode_supplier_name(self):
        res = self.client.post(
            "/admin/suppliers/agreements/123/unapprove?next_status=on-hold",
            data={"nameOfOrganisation": u"Test O\u2019Connor"},
        )

        self.data_api_client.unapprove_agreement_for_countersignature.assert_called_once_with(
            '123',
            'test@example.com',
            '1234',
        )
        self.assert_flashes(
            u"The agreement for Test O\u2019Connor had its approval cancelled. You can approve it again at any time.",
        )
        assert res.status_code == 302

        parsed_location = urlparse(res.location)
        assert parsed_location.path == "/admin/suppliers/4321/agreements/g-cloud-99p-world"
        assert parse_qs(parsed_location.query) == {"next_status": ["on-hold"]}


@mock.patch('app.main.views.suppliers.data_api_client', autospec=True)
@mock.patch('app.main.views.suppliers.get_signed_url')
@mock.patch('app.main.views.suppliers.s3')
class TestCorrectButtonsAreShownDependingOnContext(LoggedInApplicationTest):
    user_role = 'admin-ccs-sourcing'

    decl_nameOfOrganization = u"\u00a3\u00a3\u00a3 4 greengrocer's"

    def set_mocks(self, s3, get_signed_url, data_api_client, **kwargs):
        data_api_client.get_supplier.return_value = {
            'suppliers': {
                "id": 1234,
            },
        }
        data_api_client.get_framework.return_value = {
            'frameworks': {
                'frameworkAgreementVersion': 'v1.0',
                'slug': 'g-cloud-8',
                'status': 'live',
            },
        }
        data_api_client.get_supplier_framework_info.return_value = {
            'frameworkInterest': {
                'agreementReturned': True,
                'agreementStatus': kwargs['agreement_status'],
                'agreementId': 4321,
                'declaration': {
                    "nameOfOrganisation": self.decl_nameOfOrganization,
                },
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

    @pytest.mark.parametrize("role, expected_code, read_only", [
        ("admin", 403, None),
        ("admin-ccs-category", 200, True),
        ("admin-ccs-sourcing", 200, False),
        ("admin-framework-manager", 200, True),
        ("admin-manager", 403, None),
    ])
    def test_get_page_should_only_be_accessible_to_specific_user_roles(
            self, s3, get_signed_url, data_api_client, role, expected_code, read_only
    ):
        self.user_role = role
        self.set_mocks(s3, get_signed_url, data_api_client, agreement_status='signed')
        response = self.client.get("/admin/suppliers/1234/agreements/g-cloud-8")
        actual_code = response.status_code
        assert actual_code == expected_code, "Unexpected response {} for role {}".format(actual_code, role)
        # No action buttons should be shown if read-only
        if read_only:
            document = html.fromstring(response.get_data(as_text=True))
            input_elems = document.xpath("//main//form//input[@type='submit']")
            assert len(input_elems) == 0

    @pytest.mark.parametrize("next_status", (None, "on-hold", "approved,countersigned",))
    def test_buttons_shown_if_ccs_admin_and_agreement_signed(self, s3, get_signed_url, data_api_client, next_status):
        self.set_mocks(s3, get_signed_url, data_api_client, agreement_status='signed')

        res = self.client.get("/admin/suppliers/1234/agreements/g-cloud-8{}".format(
            "" if next_status is None else "?next_status={}".format(next_status)
        ))
        assert res.status_code == 200

        data = res.get_data(as_text=True)
        document = html.fromstring(data)

        assert "Cancel acceptance" not in data

        accept_input_elems = document.xpath("//form//input[@type='submit'][@value='Accept and continue']")
        assert len(accept_input_elems) == 1
        accept_form_elem = accept_input_elems[0].xpath("ancestor::form")[0]
        assert self._parsed_url_matches(
            accept_form_elem.attrib["action"],
            "/admin/suppliers/agreements/4321/approve",
            {} if next_status is None else {"next_status": [next_status]},
        )
        assert accept_form_elem.attrib["method"].lower() == "post"
        assert accept_form_elem.xpath("input[@name='csrf_token']")
        assert accept_form_elem.xpath("input[@name='nameOfOrganisation'][@value=$n]", n=self.decl_nameOfOrganization)

        hold_input_elems = document.xpath("//form//input[@type='submit'][@value='Put on hold and continue']")
        assert len(hold_input_elems) == 1
        hold_form_elem = hold_input_elems[0].xpath("ancestor::form")[0]
        assert self._parsed_url_matches(
            hold_form_elem.attrib["action"],
            "/admin/suppliers/agreements/4321/on-hold",
            {} if next_status is None else {"next_status": [next_status]},
        )
        assert hold_form_elem.attrib["method"].lower() == "post"
        assert hold_form_elem.xpath("input[@name='csrf_token']")
        assert hold_form_elem.xpath("input[@name='nameOfOrganisation'][@value=$n]", n=self.decl_nameOfOrganization)

        assert not document.xpath("//h2[normalize-space(string())='Accepted by']")

        next_a_elems = document.xpath("//a[normalize-space(string())='Next agreement']")
        assert len(next_a_elems) == 1
        assert self._parsed_url_matches(
            next_a_elems[0].attrib["href"],
            "/admin/suppliers/1234/agreements/g-cloud-8/next",
            {} if next_status is None else {"status": [next_status]},
        )

        assert not document.xpath("//input[@type='submit'][contains(@value, 'Cancel')]")
        assert not document.xpath("//form[contains(@action, 'unapprove')]")

    @pytest.mark.parametrize("next_status", (None, "on-hold", "approved,countersigned",))
    def test_only_counter_sign_shown_if_agreement_on_hold(self, s3, get_signed_url, data_api_client, next_status):
        self.set_mocks(s3, get_signed_url, data_api_client, agreement_status='on-hold')

        res = self.client.get("/admin/suppliers/1234/agreements/g-cloud-8{}".format(
            "" if next_status is None else "?next_status={}".format(next_status)
        ))
        assert res.status_code == 200

        data = res.get_data(as_text=True)
        document = html.fromstring(data)

        assert "Cancel acceptance" not in data

        accept_input_elems = document.xpath("//form//input[@type='submit'][@value='Accept and continue']")
        assert len(accept_input_elems) == 1
        accept_form_elem = accept_input_elems[0].xpath("ancestor::form")[0]
        assert self._parsed_url_matches(
            accept_form_elem.attrib["action"],
            "/admin/suppliers/agreements/4321/approve",
            {} if next_status is None else {"next_status": [next_status]},
        )
        assert accept_form_elem.attrib["method"].lower() == "post"
        assert accept_form_elem.xpath("input[@name='csrf_token']")
        assert accept_form_elem.xpath("input[@name='nameOfOrganisation'][@value=$n]", n=self.decl_nameOfOrganization)

        assert "Put on hold and continue" not in data
        assert not document.xpath("//h2[normalize-space(string())='Accepted by']")

        next_a_elems = document.xpath("//a[normalize-space(string())='Next agreement']")
        assert len(next_a_elems) == 1
        assert self._parsed_url_matches(
            next_a_elems[0].attrib["href"],
            "/admin/suppliers/1234/agreements/g-cloud-8/next",
            {} if next_status is None else {"status": [next_status]},
        )

        assert not document.xpath("//input[@type='submit'][contains(@value, 'Cancel')]")
        assert not document.xpath("//form[contains(@action, 'unapprove')]")

    @pytest.mark.parametrize("next_status", (None, "on-hold", "approved,countersigned",))
    def test_cancel_shown_if_agreement_approved(self, s3, get_signed_url, data_api_client, next_status):
        self.set_mocks(s3, get_signed_url, data_api_client, agreement_status='approved')

        res = self.client.get("/admin/suppliers/1234/agreements/g-cloud-8{}".format(
            "" if next_status is None else "?next_status={}".format(next_status)
        ))
        assert res.status_code == 200

        data = res.get_data(as_text=True)
        document = html.fromstring(data)

        assert "Accept and continue" not in data
        assert "Put on hold and continue" not in data
        assert len(document.xpath("//h2[normalize-space(string())='Accepted by']")) == 1

        cancel_input_elems = document.xpath("//form//input[@type='submit'][@value='Cancel acceptance']")
        assert len(cancel_input_elems) == 1
        cancel_form_elem = cancel_input_elems[0].xpath("ancestor::form")[0]
        assert self._parsed_url_matches(
            cancel_form_elem.attrib["action"],
            "/admin/suppliers/agreements/4321/unapprove",
            {} if next_status is None else {"next_status": [next_status]},
        )
        assert cancel_form_elem.attrib["method"].lower() == "post"
        assert cancel_form_elem.xpath("input[@name='csrf_token']")
        assert cancel_form_elem.xpath("input[@name='nameOfOrganisation'][@value=$n]", n=self.decl_nameOfOrganization)

        next_a_elems = document.xpath("//a[normalize-space(string())='Next agreement']")
        assert len(next_a_elems) == 1
        assert self._parsed_url_matches(
            next_a_elems[0].attrib["href"],
            "/admin/suppliers/1234/agreements/g-cloud-8/next",
            {} if next_status is None else {"status": [next_status]},
        )

    @pytest.mark.parametrize("next_status", (None, "on-hold", "approved,countersigned",))
    def test_none_shown_if_agreement_countersigned(self, s3, get_signed_url, data_api_client, next_status):
        self.set_mocks(s3, get_signed_url, data_api_client, agreement_status='countersigned')

        res = self.client.get("/admin/suppliers/1234/agreements/g-cloud-8{}".format(
            "" if next_status is None else "?next_status={}".format(next_status)
        ))
        assert res.status_code == 200

        data = res.get_data(as_text=True)
        document = html.fromstring(data)

        assert "Accept and continue" not in data
        assert "Put on hold and continue" not in data
        assert "Cancel acceptance" not in data
        assert len(document.xpath("//h2[normalize-space(string())='Accepted by']")) == 1

        next_a_elems = document.xpath("//a[normalize-space(string())='Next agreement']")
        assert len(next_a_elems) == 1
        assert self._parsed_url_matches(
            next_a_elems[0].attrib["href"],
            "/admin/suppliers/1234/agreements/g-cloud-8/next",
            {} if next_status is None else {"status": [next_status]},
        )

        assert not document.xpath("//input[@type='submit'][contains(@value, 'Cancel')]")
        assert not document.xpath("//form[contains(@action, 'unapprove')]")
