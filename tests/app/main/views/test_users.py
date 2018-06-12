# -*- coding: utf-8 -*-
import copy

from freezegun import freeze_time
import mock
import pytest
from lxml import html

from ...helpers import LoggedInApplicationTest


class TestUsersView(LoggedInApplicationTest):

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.users.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()
        self.data_api_client.get_user.return_value = self.load_example_listing("user_response")

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    @pytest.mark.parametrize("role,expected_code", [
        ("admin", 200),
        ("admin-ccs-category", 200),
        ("admin-ccs-sourcing", 403),
        ("admin-manager", 403),
        ("admin-framework-manager", 403),
    ])
    def test_find_users_page_is_only_accessible_to_specific_user_roles(self, role, expected_code):
        self.user_role = role
        response = self.client.get('/admin/users?email_address=some@email.com')
        actual_code = response.status_code
        assert actual_code == expected_code, "Unexpected response {} for role {}".format(actual_code, role)

    def test_should_show_find_users_page(self):
        self.data_api_client.get_user.return_value = None
        response = self.client.get('/admin/users')
        page_html = response.get_data(as_text=True)
        document = html.fromstring(page_html)
        heading = document.xpath(
            '//header[@class="page-heading page-heading-without-breadcrumb"]//h1/text()')[0].strip()

        assert response.status_code == 200
        assert "Sorry, we couldn't find an account with that email address" not in page_html
        assert heading == "Find a user"

    def test_should_be_a_404_if_user_not_found(self):
        self.data_api_client.get_user.return_value = None
        response = self.client.get('/admin/users?email_address=some@email.com')
        assert response.status_code == 404

        document = html.fromstring(response.get_data(as_text=True))

        page_title = document.xpath(
            '//p[@class="banner-message"]//text()')[0].strip()
        assert page_title == "Sorry, we couldn't find an account with that email address"

        page_title = document.xpath(
            '//p[@class="summary-item-no-content"]//text()')[0].strip()
        assert page_title == "No users to show"

    def test_should_be_a_404_if_no_email_provided(self):
        self.data_api_client.get_user.return_value = None
        response = self.client.get('/admin/users?email_address=')
        assert response.status_code == 404

        document = html.fromstring(response.get_data(as_text=True))

        page_title = document.xpath(
            '//p[@class="banner-message"]//text()')[0].strip()
        assert page_title == "Sorry, we couldn't find an account with that email address"

        page_title = document.xpath(
            '//p[@class="summary-item-no-content"]//text()')[0].strip()
        assert page_title == "No users to show"

    def test_should_show_buyer_user(self):
        buyer = self.load_example_listing("user_response")
        buyer.pop('supplier', None)
        buyer['users']['role'] = 'buyer'
        self.data_api_client.get_user.return_value = buyer
        response = self.client.get('/admin/users?email_address=test.user@sme.com')
        assert response.status_code == 200

        document = html.fromstring(response.get_data(as_text=True))

        name = document.xpath(
            '//tr[@class="summary-item-row"]//td/span/text()')[0].strip()
        assert name == "Test User"

        role = document.xpath(
            '//tr[@class="summary-item-row"]//td/span/text()')[1].strip()
        assert role == "buyer"

        supplier = document.xpath(
            '//tr[@class="summary-item-row"]//td/span/text()')[2].strip()
        assert supplier == ''

        last_login = document.xpath(
            '//tr[@class="summary-item-row"]//td/span/text()')[3].strip()
        assert last_login == '09:33:53'

        last_login_day = document.xpath(
            '//tr[@class="summary-item-row"]//td/span/text()')[4].strip()
        assert last_login_day == '23 July'

        last_password_changed = document.xpath(
            '//tr[@class="summary-item-row"]//td/span/text()')[5].strip()
        assert last_password_changed == '12:46:01'

        last_password_changed_day = document.xpath(
            '//tr[@class="summary-item-row"]//td/span/text()')[6].strip()
        assert last_password_changed_day == '29 June'

        locked = document.xpath(
            '//tr[@class="summary-item-row"]//td/span/text()')[7].strip()
        assert locked == 'No'

        button = document.xpath(
            '//input[@class="button-destructive"]')[0].value
        assert button == 'Deactivate'

    def test_should_show_supplier_user(self):
        response = self.client.get('/admin/users?email_address=test.user@sme.com')
        assert response.status_code == 200

        document = html.fromstring(response.get_data(as_text=True))

        role = document.xpath(
            '//tr[@class="summary-item-row"]//td/span/text()')[1].strip()
        assert role == "supplier"

        supplier = document.xpath(
            '//tr[@class="summary-item-row"]//td/span/a/text()')[0].strip()
        assert supplier == 'SME Corp UK Limited'

        supplier_link = document.xpath(
            '//tr[@class="summary-item-row"]//td/span/a')[0]
        assert supplier_link.attrib['href'] == '/admin/suppliers?supplier_id=1000'

    def test_should_show_unlock_button(self):
        buyer = self.load_example_listing("user_response")
        buyer['users']['locked'] = True

        self.data_api_client.get_user.return_value = buyer
        response = self.client.get('/admin/users?email_address=test.user@sme.com')
        assert response.status_code == 200

        document = html.fromstring(response.get_data(as_text=True))

        unlock_button = document.xpath(
            '//input[@class="button-secondary"]')[0].attrib['value']
        unlock_link = document.xpath(
            '//tr[@class="summary-item-row"]//td/span/form')[0]
        return_link = document.xpath(
            '//tr[@class="summary-item-row"]//td/span/form/input')[1]
        assert unlock_link.attrib['action'] == '/admin/suppliers/users/999/unlock'
        assert unlock_button == 'Unlock'
        assert return_link.attrib['value'] == '/admin/users?email_address=test.user%40sme.com'

    def test_should_show_deactivate_button(self):
        response = self.client.get('/admin/users?email_address=test.user@sme.com')
        assert response.status_code == 200

        document = html.fromstring(response.get_data(as_text=True))

        deactivate_button = document.xpath(
            '//input[@class="button-destructive"]')[0].attrib['value']
        deactivate_link = document.xpath(
            '//tr[@class="summary-item-row"]//td/span/form')[0]
        return_link = document.xpath(
            '//tr[@class="summary-item-row"]//td/span/form/input')[1]
        assert deactivate_link.attrib['action'] == '/admin/suppliers/users/999/deactivate'
        assert deactivate_button == 'Deactivate'
        assert return_link.attrib['value'] == '/admin/users?email_address=test.user%40sme.com'


class TestUserListPage(LoggedInApplicationTest):
    user_role = 'admin-framework-manager'

    _framework = {
        'name': 'G-Cloud 9',
        'slug': 'g-cloud-9',
        'status': 'live'
    }

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.users.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    @pytest.mark.parametrize("role,expected_code", [
        ("admin", 403),
        ("admin-ccs-category", 403),
        ("admin-ccs-sourcing", 403),
        ("admin-framework-manager", 200),
        ("admin-manager", 403),
    ])
    def test_get_user_lists_is_only_accessible_to_specific_user_roles(self, role, expected_code):
        self.user_role = role
        response = self.client.get("/admin/frameworks/g-cloud-9/users")
        actual_code = response.status_code
        assert actual_code == expected_code, "Unexpected response {} for role {}".format(actual_code, role)

    def test_get_user_lists_shows_framework_name_in_heading(self):
        self.data_api_client.get_framework.return_value = {"frameworks": self._framework}
        response = self.client.get("/admin/frameworks/g-cloud-9/users")
        document = html.fromstring(response.get_data(as_text=True))

        page_heading = document.xpath(
            '//h1//text()')[0].strip()
        assert page_heading == "Download supplier lists for G-Cloud 9"


class TestUsersExport(LoggedInApplicationTest):
    user_role = 'admin-framework-manager'
    _bad_statuses = ['coming', 'expired']

    _valid_framework = {
        'name': 'G-Cloud 7',
        'slug': 'g-cloud-7',
        'status': 'live'
    }

    _invalid_framework = {
        'name': 'G-Cloud 8',
        'slug': 'g-cloud-8',
        'status': 'coming'
    }

    _supplier_user = {
        "application_result": "fail",
        "application_status": "no_application",
        "declaration_status": "unstarted",
        "framework_agreement": False,
        "supplier_id": 1,
        "email address": "test.user@sme.com",
        "user_name": "Test User",
        "variations_agreed": "var1",
        "published_service_count": "0",
        "user_research_opted_in": True
    }

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.users.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    @pytest.mark.parametrize("role, url_params, expected_code", [
        ("admin", "?user_research_opted_in=True", 200),
        ("admin", "?user_research_opted_in=False", 403),
        ("admin-ccs-category", "", 403),
        ("admin-ccs-sourcing", "", 403),
        ("admin-framework-manager", "?on_framework_only=True", 200),
        ("admin-framework-manager", "?on_framework_only=False", 200),
        ("admin-manager", "", 403),
    ])
    def test_supplier_user_csvs_are_only_accessible_to_specific_user_roles(self, role, url_params, expected_code):
        self.user_role = role
        users = [self._supplier_user]
        self.data_api_client.export_users.return_value = {"users": copy.copy(users)}
        self.data_api_client.find_frameworks.return_value = {"frameworks": [self._valid_framework]}
        self.data_api_client.get_framework.return_value = {"frameworks": self._valid_framework}

        response = self.client.get(
            '/admin/frameworks/{}/users/download{}'.format(
                self._valid_framework['slug'],
                url_params
            ),
            data={'framework_slug': self._valid_framework['slug']}
        )

        assert response.status_code == expected_code

    def test_download_csv_for_all_framework_users(self):
        users = [self._supplier_user]

        self.data_api_client.export_users.return_value = {"users": copy.copy(users)}
        self.data_api_client.find_frameworks.return_value = {"frameworks": [self._valid_framework]}

        self.data_api_client.get_framework.return_value = {"frameworks": self._valid_framework}
        response = self.client.get(
            '/admin/frameworks/{}/users/download'.format(
                self._valid_framework['slug']
            ),

            data={'framework_slug': self._valid_framework['slug']}
        )
        assert response.status_code == 200
        assert response.mimetype == 'text/csv'
        assert (response.headers['Content-Disposition'] ==
                'attachment;filename=g-cloud-7-suppliers-who-applied-or-started-application.csv')

        rows = [line.split(",") for line in response.get_data(as_text=True).splitlines()]

        assert len(rows) == len(users) + 1
        expected_headings = [
            'email address',
            'user_name',
            'supplier_id',
            'declaration_status',
            'application_status',
            'application_result',
            'framework_agreement',
            'variations_agreed',
            'published_service_count',
        ]

        assert rows[0] == expected_headings
        # All users returned from the API should appear in the CSV
        for index, user in enumerate(users):
            assert sorted(
                [str(val) for key, val in user.items() if key in expected_headings]
            ) == sorted(rows[index + 1])

    def test_download_csv_for_on_framework_only(self):
        users = [
            self._supplier_user,
            {
                "application_result": "pass",
                "application_status": "application",
                "declaration_status": "complete",
                "framework_agreement": False,
                "supplier_id": 2,
                "email address": "test.user@sme2.com",
                "user_name": "Test User 2",
                "variations_agreed": "",
                "published_service_count": 0,
            }
        ]

        self.data_api_client.export_users.return_value = {"users": copy.copy(users)}
        self.data_api_client.find_frameworks.return_value = {"frameworks": [self._valid_framework]}

        self.data_api_client.get_framework.return_value = {"frameworks": self._valid_framework}
        response = self.client.get(
            '/admin/frameworks/{}/users/download?on_framework_only=True'.format(
                self._valid_framework['slug'],
            ),
            data={'framework_slug': self._valid_framework['slug']}
        )
        assert response.status_code == 200
        assert response.mimetype == 'text/csv'
        assert response.headers['Content-Disposition'] == 'attachment;filename=suppliers-on-g-cloud-7.csv'

        rows = [line.split(",") for line in response.get_data(as_text=True).splitlines()]

        assert len(rows) == 2
        assert rows[0] == ["email address", "user_name", "supplier_id"]
        # Only users with application_result = "pass" should appear in the CSV
        assert rows[1] == ["test.user@sme2.com", "Test User 2", "2"]


class TestSuppliersExport(LoggedInApplicationTest):
    user_role = 'admin-framework-manager'

    _valid_framework = {
        'name': 'Digital Outcomes and Specialists 2',
        'slug': 'digital-outcomes-and-specialists-2',
        'status': 'live',
        'lots': [
            {"id": 1, "slug": "digital-outcomes"},
            {"id": 2, "slug": "digital-specialists"},
            {"id": 3, "slug": "user-research-studios"},
            {"id": 4, "slug": "user-research-participants"}
        ]
    }

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.users.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    @pytest.mark.parametrize("role, expected_code", [
        ("admin", 200),
        ("admin-ccs-category", 403),
        ("admin-ccs-sourcing", 403),
        ("admin-framework-manager", 200),
        ("admin-manager", 403),
    ])
    def test_supplier_csv_is_only_accessible_to_specific_user_roles(self, role, expected_code):
        self.user_role = role
        self.data_api_client.export_suppliers.return_value = {"suppliers": []}
        self.data_api_client.find_frameworks.return_value = {"frameworks": [self._valid_framework]}
        self.data_api_client.get_framework.return_value = {"frameworks": self._valid_framework}

        response = self.client.get(
            '/admin/frameworks/{}/suppliers/download'.format(self._valid_framework['slug'])
        )

        assert response.status_code == expected_code

    def test_download_supplier_csv_for_framework_users(self):
        list_of_expected_supplier_results = [
            {
                'supplier_id': 1,
                'application_result': 'no result',
                'application_status': 'no_application',
                'declaration_status': 'unstarted',
                'framework_agreement': False,
                'supplier_name': "Supplier 1",
                'supplier_organisation_size': "small",
                'duns_number': "100000001",
                'registered_name': 'Registered Supplier Name 1',
                'companies_house_number': 'ABC123',
                "published_services_count": {
                    "digital-outcomes": 2,
                    "digital-specialists": 0,
                    "user-research-studios": 1,
                    "user-research-participants": 0,
                },
                "contact_information": {
                    'contact_name': 'Contact for Supplier 1',
                    'contact_email': '1@contact.com',
                    'contact_phone_number': '12345',
                    'address_first_line': '7 Gem Lane',
                    'address_city': 'Cantelot',
                    'address_postcode': 'CN1A 1AA',
                    'address_country': 'country:GB',
                },
                'variations_agreed': '',
            },
            {
                'supplier_id': 2,
                'application_result': 'pass',
                'application_status': 'application',
                'declaration_status': 'complete',
                'framework_agreement': True,
                'supplier_name': "Supplier 2",
                'supplier_organisation_size': "micro",
                'duns_number': "200000002",
                'registered_name': 'Registered Supplier Name 2',
                'companies_house_number': 'ABC456',
                "published_services_count": {
                    "digital-outcomes": 2,
                    "digital-specialists": 2,
                    "user-research-studios": 2,
                    "user-research-participants": 2,
                },
                "contact_information": {
                    'contact_name': 'Contact for Supplier 2',
                    'contact_email': '2@contact.com',
                    'contact_phone_number': '22345',
                    'address_first_line': '27 Gem Lane',
                    'address_city': 'Cantelot',
                    'address_postcode': 'CN2A 2AA',
                    'address_country': 'country:GB',
                },
                'variations_agreed': "1,2",
            }
        ]
        self.data_api_client.export_suppliers.return_value = {"suppliers": list_of_expected_supplier_results}
        self.data_api_client.find_frameworks.return_value = {"frameworks": [self._valid_framework]}

        self.data_api_client.get_framework.return_value = {"frameworks": self._valid_framework}
        response = self.client.get(
            '/admin/frameworks/{}/suppliers/download'.format(
                self._valid_framework['slug']
            )
        )
        assert response.status_code == 200
        assert response.mimetype == 'text/csv'
        assert (response.headers['Content-Disposition'] ==
                'attachment;filename=suppliers-on-digital-outcomes-and-specialists-2.csv')

        rows = response.get_data(as_text=True).splitlines()

        assert len(rows) == len(list_of_expected_supplier_results) + 1
        expected_headings = [
            "supplier_id",
            "supplier_name",
            "supplier_organisation_size",
            "duns_number",
            "companies_house_number",
            "registered_name",
            "declaration_status",
            "application_status",
            "application_result",
            "framework_agreement",
            "variations_agreed",
            "total_number_of_services",
            "service-count-digital-outcomes",
            "service-count-digital-specialists",
            "service-count-user-research-studios",
            "service-count-user-research-participants",
            'contact_name',
            'contact_email',
            'contact_phone_number',
            'address_first_line',
            'address_city',
            'address_postcode',
            'address_country',
        ]

        assert rows[0] == ",".join(expected_headings)
        assert rows[1] == ",".join([
            '1', 'Supplier 1', 'small', '100000001', 'ABC123', 'Registered Supplier Name 1',
            'unstarted', 'no_application', 'no result', 'False', '',
            '3',  # Total number of services
            '2', '0', '1', '0',  # Services for each lot
            'Contact for Supplier 1',
            '1@contact.com', '12345',
            '7 Gem Lane', 'Cantelot', 'CN1A 1AA', 'country:GB'
        ])
        assert rows[2] == ",".join([
            '2', 'Supplier 2', 'micro', '200000002', 'ABC456', 'Registered Supplier Name 2',
            'complete', 'application', 'pass', 'True',
            '"1,2"',  # Comma separated list of agreed variations
            '8',
            '2', '2', '2', '2',
            'Contact for Supplier 2',
            '2@contact.com', '22345',
            '27 Gem Lane', 'Cantelot', 'CN2A 2AA', 'country:GB'
        ])


class TestBuyersExport(LoggedInApplicationTest):
    user_role = "admin-framework-manager"

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.users.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    @pytest.mark.parametrize('user_role', ('admin', 'admin-framework-manager'))
    def test_csv_is_sorted_by_name(self, user_role):
        self.user_role = user_role
        self.data_api_client.find_users_iter.return_value = [
            {
                'id': 1,
                "name": "Zebedee",
                "emailAddress": "zebedee@gov.uk",
                "phoneNumber": "01234567891",
                "createdAt": "2016-08-04T12:00:00.000000Z",
                "userResearchOptedIn": True
            },
            {
                'id': 2,
                "name": "Dougal",
                "emailAddress": "dougal@gov.uk",
                "phoneNumber": "01234567891",
                "createdAt": "2016-08-05T12:00:00.000000Z",
                "userResearchOptedIn": True
            },
            {
                'id': 3,
                "name": "Brian",
                "emailAddress": "brian@gov.uk",
                "phoneNumber": "01234567891",
                "createdAt": "2016-08-06T12:00:00.000000Z",
                "userResearchOptedIn": True
            },
            {
                'id': 4,
                "name": "Florence",
                "emailAddress": "florence@gov.uk",
                "phoneNumber": "01234567891",
                "createdAt": "2016-08-07T12:00:00.000000Z",
                "userResearchOptedIn": True
            },
        ]

        response = self.client.get('/admin/users/download/buyers')

        assert response.status_code == 200

        rows = [line.split(",") for line in response.get_data(as_text=True).splitlines()]

        assert [row[1] for row in rows[1:5]] == ['Brian', 'Dougal', 'Florence', 'Zebedee']

    @pytest.mark.parametrize('user_role', ('admin', 'admin-framework-manager'))
    def test_response_is_a_csv(self, user_role):
        self.user_role = user_role
        self.data_api_client.find_users_iter.return_value = [
            {
                'id': 1,
                "name": "Chris",
                "emailAddress": "chris@gov.uk",
                "phoneNumber": "01234567891",
                "createdAt": "2016-08-04T12:00:00.000000Z",
                "userResearchOptedIn": True
            },
        ]

        response = self.client.get('/admin/users/download/buyers')

        assert response.mimetype == 'text/csv'

    @pytest.mark.parametrize('user_role', ('admin', 'admin-framework-manager'))
    def test_filename_includes_a_timestamp(self, user_role):
        self.user_role = user_role
        with freeze_time("2016-08-05 16:00:00"):
            self.data_api_client.find_users_iter.return_value = [
                {
                    'id': 1,
                    "name": "Chris",
                    "emailAddress": "chris@gov.uk",
                    "phoneNumber": "01234567891",
                    "createdAt": "2016-08-04T12:00:00.000000Z",
                },
            ]

            response = self.client.get('/admin/users/download/buyers')
            assert '2016-08-05-at-16-00-00' in response.headers['Content-Disposition']

    @pytest.mark.parametrize("role, expected_code", [
        ("admin", 200),
        ("admin-ccs-category", 403),
        ("admin-ccs-sourcing", 403),
        ("admin-framework-manager", 200),
        ("admin-manager", 403),
    ])
    def test_buyer_csv_is_only_accessible_to_specific_user_roles(self, role, expected_code):
        self.user_role = role
        self.data_api_client.find_users_iter.return_value = [
            {
                'id': 1,
                "name": "Chris",
                "emailAddress": "chris@gov.uk",
                "phoneNumber": "01234567891",
                "createdAt": "2016-08-04T12:00:00.000000Z",
            }
        ]

        response = self.client.get('/admin/users/download/buyers')
        actual_code = response.status_code
        assert actual_code == expected_code, "Unexpected response {} for role {}".format(actual_code, role)

    def test_response_data_has_correct_buyer_info_for_framework_manager_role(self):
        self.user_role = "admin-framework-manager"
        self.data_api_client.find_users_iter.return_value = [
            {
                'id': 1,
                "name": "Chris",
                "emailAddress": "chris@gov.uk",
                "phoneNumber": "01234567891",
                "createdAt": "2016-08-04T12:00:00.000000Z",
            },
            {
                'id': 2,
                "name": "Topher",
                "emailAddress": "topher@gov.uk",
                "phoneNumber": "01234567891",
                "createdAt": "2016-08-05T12:00:00.000000Z",
            },
        ]
        with freeze_time("2016-08-05 16:00:00"):
            response = self.client.get('/admin/users/download/buyers')
        assert response.status_code == 200

        rows = [line.split(",") for line in response.get_data(as_text=True).splitlines()]

        assert response.headers['Content-Disposition'] == 'attachment;filename=all-buyers-on-2016-08-05-at-16-00-00.csv'
        assert len(rows) == 3
        assert rows == [
            ['email address', 'name'],
            ['chris@gov.uk', 'Chris'],
            ['topher@gov.uk', 'Topher'],
        ]

    def test_response_data_has_correct_buyer_info_for_admin_role(self):
        self.user_role = "admin"

        self.data_api_client.find_users_iter.return_value = [
            {
                'id': 1,
                "name": "Chris",
                "emailAddress": "chris@gov.uk",
                "phoneNumber": "01234567891",
                "createdAt": "2016-08-04T12:00:00.000000Z",
                "userResearchOptedIn": True
            },
            {
                'id': 2,
                "name": "Topher",
                "emailAddress": "topher@gov.uk",
                "phoneNumber": "01234567891",
                "createdAt": "2016-08-05T12:00:00.000000Z",
                "userResearchOptedIn": False
            },
            {
                'id': 3,
                "name": "Winifred",
                "emailAddress": "winifred@gov.uk",
                "phoneNumber": "34567890987",
                "createdAt": "2016-08-02T12:00:00.000000Z",
                "userResearchOptedIn": True
            },
        ]
        with freeze_time("2016-08-05 16:00:00"):
            response = self.client.get('/admin/users/download/buyers')
        assert response.status_code == 200

        rows = [line.split(",") for line in response.get_data(as_text=True).splitlines()]

        assert (
            response.headers['Content-Disposition'] ==
            'attachment;filename=user-research-buyers-on-2016-08-05-at-16-00-00.csv'
        )
        assert len(rows) == 3
        assert rows == [
            ['email address', 'name'],
            ['chris@gov.uk', 'Chris'],
            ['winifred@gov.uk', 'Winifred'],
        ]


class TestUserResearchParticipantsExport(LoggedInApplicationTest):
    user_role = 'admin'

    _valid_framework = {
        'name': 'G-Cloud 7',
        'slug': 'g-cloud-7',
        'status': 'live'
    }

    _invalid_framework = {
        'name': 'G-Cloud 8',
        'slug': 'g-cloud-8',
        'status': 'coming'
    }

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.users.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    @pytest.mark.parametrize(
        ('role', 'exists'),
        (
            ('admin', True),
            ('admin-ccs-category', False),
            ('admin-ccs-sourcing', False),
            ('admin-manager', False),
            ('admin-framework-manager', False)
        )
    )
    def test_correct_role_can_view_download_buyer_user_research_participants_link(self, role, exists):
        self.user_role = role

        xpath = "//a[@href='{href}'][normalize-space(text()) = '{selector_text}']".format(
            href='/admin/users/download/buyers',
            selector_text='Download list of potential user research participants'
        )

        response = self.client.get('/admin')
        assert response.status_code == 200

        document = html.fromstring(response.get_data(as_text=True))
        assert bool(document.xpath(xpath)) is exists

    @pytest.mark.parametrize(
        ('role', 'exists'),
        (
            ('admin', True),
            ('admin-ccs-category', False),
            ('admin-ccs-sourcing', False),
            ('admin-manager', False),
            ('admin-framework-manager', False)
        )
    )
    def test_correct_role_can_view_supplier_user_research_participants_link(self, role, exists):
        self.user_role = role

        xpath = "//a[@href='{href}'][normalize-space(text()) = '{selector_text}']".format(
            href='/admin/users/download/suppliers',
            selector_text='Download lists of potential user research participants'
        )

        response = self.client.get('/admin')
        assert response.status_code == 200

        document = html.fromstring(response.get_data(as_text=True))
        assert bool(document.xpath(xpath)) is exists

    @pytest.mark.parametrize(
        ('role', 'status_code'),
        (
            ('admin', 200),
            ('admin-ccs-category', 403),
            ('admin-ccs-sourcing', 403),
            ('admin-manager', 403),
            ('admin-framework-manager', 403)
        )
    )
    def test_correct_role_can_view_supplier_user_research_participants_page(self, role, status_code):
        self.user_role = role

        response = self.client.get('/admin/users/download/suppliers')
        assert response.status_code == status_code

    def test_supplier_csvs_shown_for_valid_frameworks(self):
        self.data_api_client.find_frameworks.return_value = {
            'frameworks': [self._valid_framework, self._invalid_framework]
        }

        response = self.client.get('/admin/users/download/suppliers')
        assert response.status_code == 200

        text = response.get_data(as_text=True)
        document = html.fromstring(text)
        href_xpath = "//a[@href='/admin/frameworks/{}/users/download?user_research_opted_in=True']"

        assert document.xpath(href_xpath.format(self._valid_framework['slug']))
        assert 'User research participants on {}'.format(self._valid_framework['name']) in text

        assert not document.xpath(href_xpath.format(self._invalid_framework['slug']))
        assert not 'User research participants on {}'.format(self._invalid_framework['name']) in text

    def test_supplier_csvs_shown_in_alphabetical_name_order(self):
        framework_1 = self._valid_framework.copy()
        framework_2 = self._valid_framework.copy()
        framework_3 = self._valid_framework.copy()
        framework_1['name'] = 'aframework_1'
        framework_2['name'] = 'bframework_1'
        framework_3['name'] = 'bframework_2'

        self.data_api_client.find_frameworks.return_value = {'frameworks': [framework_3, framework_1, framework_2]}

        response = self.client.get('/admin/users/download/suppliers')
        assert response.status_code == 200

        text = response.get_data(as_text=True)

        framework_1_link_text = 'User research participants on ' + framework_1['name']
        framework_2_link_text = 'User research participants on ' + framework_2['name']
        framework_3_link_text = 'User research participants on ' + framework_3['name']
        assert text.find(framework_1_link_text) < text.find(framework_2_link_text) < text.find(framework_3_link_text)
