# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import copy
from datetime import datetime

import mock
import pytest
import six
from dmapiclient import HTTPError
from lxml import html

from ...helpers import LoggedInApplicationTest


@mock.patch('app.main.views.users.data_api_client')
class TestUsersView(LoggedInApplicationTest):
    @pytest.mark.parametrize("role,expected_code", [
        ("admin", 200),
        ("admin-ccs-category", 200),
        ("admin-ccs-sourcing", 403),
        ("admin-manager", 403),
        ("admin-framework-manager", 403),
    ])
    def test_find_users_page_is_only_accessible_to_specific_user_roles(self, data_api_client, role, expected_code):
        self.user_role = role
        data_api_client.get_user.return_value = self.load_example_listing("user_response")
        response = self.client.get('/admin/users?email_address=some@email.com')
        actual_code = response.status_code
        assert actual_code == expected_code, "Unexpected response {} for role {}".format(actual_code, role)

    def test_should_show_find_users_page(self, data_api_client):
        data_api_client.get_user.return_value = None
        response = self.client.get('/admin/users')
        page_html = response.get_data(as_text=True)
        document = html.fromstring(page_html)
        heading = document.xpath(
            '//header[@class="page-heading page-heading-without-breadcrumb"]//h1/text()')[0].strip()

        assert response.status_code == 200
        assert "Sorry, we couldn't find an account with that email address" not in page_html
        assert heading == "Find a user"

    def test_should_be_a_404_if_user_not_found(self, data_api_client):
        data_api_client.get_user.return_value = None
        response = self.client.get('/admin/users?email_address=some@email.com')
        assert response.status_code == 404

        document = html.fromstring(response.get_data(as_text=True))

        page_title = document.xpath(
            '//p[@class="banner-message"]//text()')[0].strip()
        assert page_title == "Sorry, we couldn't find an account with that email address"

        page_title = document.xpath(
            '//p[@class="summary-item-no-content"]//text()')[0].strip()
        assert page_title == "No users to show"

    def test_should_be_a_404_if_no_email_provided(self, data_api_client):
        data_api_client.get_user.return_value = None
        response = self.client.get('/admin/users?email_address=')
        assert response.status_code == 404

        document = html.fromstring(response.get_data(as_text=True))

        page_title = document.xpath(
            '//p[@class="banner-message"]//text()')[0].strip()
        assert page_title == "Sorry, we couldn't find an account with that email address"

        page_title = document.xpath(
            '//p[@class="summary-item-no-content"]//text()')[0].strip()
        assert page_title == "No users to show"

    def test_should_show_buyer_user(self, data_api_client):
        buyer = self.load_example_listing("user_response")
        buyer.pop('supplier', None)
        buyer['users']['role'] = 'buyer'
        data_api_client.get_user.return_value = buyer
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
        assert last_login == '10:33:53'

        last_login_day = document.xpath(
            '//tr[@class="summary-item-row"]//td/span/text()')[4].strip()
        assert last_login_day == '23 July'

        last_password_changed = document.xpath(
            '//tr[@class="summary-item-row"]//td/span/text()')[5].strip()
        assert last_password_changed == '13:46:01'

        last_password_changed_day = document.xpath(
            '//tr[@class="summary-item-row"]//td/span/text()')[6].strip()
        assert last_password_changed_day == '29 June'

        locked = document.xpath(
            '//tr[@class="summary-item-row"]//td/span/text()')[7].strip()
        assert locked == 'No'

        button = document.xpath(
            '//input[@class="button-destructive"]')[0].value
        assert button == 'Deactivate'

    def test_should_show_supplier_user(self, data_api_client):
        buyer = self.load_example_listing("user_response")
        data_api_client.get_user.return_value = buyer
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

    def test_should_show_unlock_button(self, data_api_client):
        buyer = self.load_example_listing("user_response")
        buyer['users']['locked'] = True

        data_api_client.get_user.return_value = buyer
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

    def test_should_show_deactivate_button(self, data_api_client):
        buyer = self.load_example_listing("user_response")

        data_api_client.get_user.return_value = buyer
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


@mock.patch('app.main.views.users.data_api_client')
class TestUserListPage(LoggedInApplicationTest):
    user_role = 'admin-framework-manager'

    _framework = {
        'name': 'G-Cloud 9',
        'slug': 'g-cloud-9',
        'status': 'live'
    }

    @pytest.mark.parametrize("role,expected_code", [
        ("admin", 403),
        ("admin-ccs-category", 403),
        ("admin-ccs-sourcing", 403),
        ("admin-framework-manager", 200),
        ("admin-manager", 403),
    ])
    def test_get_user_lists_is_only_accessible_to_specific_user_roles(self, data_api_client, role, expected_code):
        self.user_role = role
        response = self.client.get("/admin/frameworks/g-cloud-9/users")
        actual_code = response.status_code
        assert actual_code == expected_code, "Unexpected response {} for role {}".format(actual_code, role)

    def test_get_user_lists_shows_framework_name_in_heading(self, data_api_client):
        data_api_client.get_framework.return_value = {"frameworks": self._framework}
        response = self.client.get("/admin/frameworks/g-cloud-9/users")
        document = html.fromstring(response.get_data(as_text=True))

        page_heading = document.xpath(
            '//h1//text()')[0].strip()
        assert page_heading == "Download supplier lists for G-Cloud 9"


@mock.patch('app.main.views.users.data_api_client')
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
        "variations_agreed": "var1"
    }

    def _return_get_user_export_response(self, data_api_client, frameworks):
            data_api_client.find_frameworks.return_value = {"frameworks": frameworks}
            return self.client.get('/admin/users/download')

    def _assert_things_about_frameworks(self, response, frameworks):

        def _assert_things_about_valid_frameworks(options, frameworks):
            valid_frameworks = [
                framework for framework in frameworks if framework['status'] not in self._bad_statuses]

            assert len(frameworks) == len(valid_frameworks)

        def _assert_things_about_invalid_frameworks(options, frameworks):
            invalid_frameworks = [
                framework for framework in frameworks if framework['status'] in self._bad_statuses]

            for framework in invalid_frameworks:
                assert framework['slug'] not in [option.xpath('input')[0].attrib['value'] for option in options]
                assert framework['name'] not in ["".join(option.xpath('text()')).strip() for option in options]

        document = html.fromstring(response.get_data(as_text=True))

        options = document.xpath(
            '//fieldset[@id="framework_slug"]/label')

        assert response.status_code == 200
        _assert_things_about_valid_frameworks(options, frameworks)
        _assert_things_about_invalid_frameworks(options, frameworks)

    def _return_user_export_response(self, data_api_client, framework, users, framework_slug=None, only_on_fwk=False):
        if framework_slug is None:
            framework_slug = framework['slug']

        # collection of users is modified in the route
        data_api_client.export_users.return_value = {"users": copy.copy(users)}
        data_api_client.find_frameworks.return_value = {"frameworks": [framework]}

        if framework_slug == framework['slug']:
            data_api_client.get_framework.return_value = {"frameworks": framework}
        else:
            data_api_client.get_framework.side_effect = HTTPError(mock.Mock(status_code=404))

        return self.client.get(
            '/admin/frameworks/{}/users/download{}'.format(
                self._valid_framework['slug'],
                '?on_framework_only=True' if only_on_fwk else ''
            ),
            data={'framework_slug': framework_slug}
        )

    ##########################################################################
    def test_get_form_with_valid_framework(self, data_api_client):
        self.user_role = 'admin-framework-manager'
        frameworks = [self._valid_framework]
        response = self._return_get_user_export_response(data_api_client, frameworks)
        assert response.status_code == 200
        self._assert_things_about_frameworks(response, frameworks)

    @pytest.mark.parametrize("role, expected_code", [
        ("admin", 200),
        ("admin-ccs-category", 403),
        ("admin-ccs-sourcing", 403),
        ("admin-framework-manager", 200),
        ("admin-manager", 403),
    ])
    def test_download_users_page_is_only_accessible_to_specific_user_roles(self, data_api_client, role, expected_code):
        self.user_role = role
        frameworks = [self._valid_framework]
        response = self._return_get_user_export_response(data_api_client, frameworks)
        actual_code = response.status_code
        assert actual_code == expected_code, "Unexpected response {} for role {}".format(actual_code, role)

    @pytest.mark.parametrize("role, expected_code", [
        ("admin", 403),
        ("admin-ccs-category", 403),
        ("admin-ccs-sourcing", 403),
        ("admin-framework-manager", 200),
        ("admin-manager", 403),
    ])
    def test_supplier_csv_is_only_accessible_to_specific_user_roles(self, data_api_client, role, expected_code):
        self.user_role = role
        framework = self._valid_framework
        users = [self._supplier_user]

        response = self._return_user_export_response(data_api_client, framework, users)
        actual_code = response.status_code
        assert actual_code == expected_code, "Unexpected response {} for role {}".format(actual_code, role)

    def test_download_csv_for_all_framework_users(self, data_api_client):
        framework = self._valid_framework
        users = [self._supplier_user]

        response = self._return_user_export_response(data_api_client, framework, users)

        assert response.status_code == 200
        assert response.mimetype == 'text/csv'
        assert (response.headers['Content-Disposition'] ==
                'attachment;filename=g-cloud-7-suppliers-who-applied-or-started-application.csv')

        rows = [line.split(",") for line in response.get_data(as_text=True).splitlines()]

        assert len(rows) == len(users) + 1
        assert rows[0] == [
            'email address',
            'user_name',
            'supplier_id',
            'declaration_status',
            'application_status',
            'application_result',
            'framework_agreement',
            'variations_agreed'
        ]
        # All users returned from the API should appear in the CSV
        for index, user in enumerate(users):
            assert sorted([six.text_type(val) for val in user.values()]) == sorted(rows[index + 1])

    def test_download_csv_for_on_framework_only(self, data_api_client):
        framework = self._valid_framework
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
                "variations_agreed": ""
            }
        ]

        response = self._return_user_export_response(data_api_client, framework, users, only_on_fwk=True)
        assert response.status_code == 200
        assert response.mimetype == 'text/csv'
        assert response.headers['Content-Disposition'] == 'attachment;filename=suppliers-on-g-cloud-7.csv'

        rows = [line.split(",") for line in response.get_data(as_text=True).splitlines()]

        assert len(rows) == 2
        assert rows[0] == ["email address", "user_name", "supplier_id"]
        # Only users with application_result = "pass" should appear in the CSV
        assert rows[1] == ["test.user@sme2.com", "Test User 2", "2"]


@mock.patch('app.main.views.users.data_api_client')
class TestBuyersExport(LoggedInApplicationTest):
    user_role = "admin-framework-manager"

    def test_response_data_has_buyer_info(self, data_api_client):
        data_api_client.find_users_iter.return_value = [
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

        response = self.client.get('/admin/users/download/buyers')
        assert response.status_code == 200

        rows = [line.split(",") for line in response.get_data(as_text=True).splitlines()]

        assert len(rows) == 3
        assert rows == [
            ['email address', 'name'],
            ['chris@gov.uk', 'Chris'],
            ['topher@gov.uk', 'Topher'],
        ]

    def test_csv_is_sorted_by_name(self, data_api_client):
        data_api_client.find_users_iter.return_value = [
            {
                'id': 1,
                "name": "Zebedee",
                "emailAddress": "zebedee@gov.uk",
                "phoneNumber": "01234567891",
                "createdAt": "2016-08-04T12:00:00.000000Z",
            },
            {
                'id': 2,
                "name": "Dougal",
                "emailAddress": "dougal@gov.uk",
                "phoneNumber": "01234567891",
                "createdAt": "2016-08-05T12:00:00.000000Z",
            },
            {
                'id': 3,
                "name": "Brian",
                "emailAddress": "brian@gov.uk",
                "phoneNumber": "01234567891",
                "createdAt": "2016-08-06T12:00:00.000000Z",
            },
            {
                'id': 4,
                "name": "Florence",
                "emailAddress": "florence@gov.uk",
                "phoneNumber": "01234567891",
                "createdAt": "2016-08-07T12:00:00.000000Z",
            },
        ]

        response = self.client.get('/admin/users/download/buyers')

        assert response.status_code == 200

        rows = [line.split(",") for line in response.get_data(as_text=True).splitlines()]

        assert [row[1] for row in rows[1:5]] == ['Brian', 'Dougal', 'Florence', 'Zebedee']

    def test_response_is_a_csv(self, data_api_client):
        data_api_client.find_users_iter.return_value = [
            {
                'id': 1,
                "name": "Chris",
                "emailAddress": "chris@gov.uk",
                "phoneNumber": "01234567891",
                "createdAt": "2016-08-04T12:00:00.000000Z",
            },
        ]

        response = self.client.get('/admin/users/download/buyers')

        assert response.mimetype == 'text/csv'

    def test_filename_includes_a_timestamp(self, data_api_client):
        with mock.patch('app.main.views.users.datetime') as mock_date:
            mock_date.utcnow.return_value = datetime(2016, 8, 5, 16, 0, 0)
            data_api_client.find_users_iter.return_value = [
                {
                    'id': 1,
                    "name": "Chris",
                    "emailAddress": "chris@gov.uk",
                    "phoneNumber": "01234567891",
                    "createdAt": "2016-08-04T12:00:00.000000Z",
                },
            ]

            response = self.client.get('/admin/users/download/buyers')

            assert (
                response.headers['Content-Disposition'] ==
                'attachment;filename=all-buyers-on-2016-08-05_at_16-00-00.csv'
            )

    @pytest.mark.parametrize("role, expected_code", [
        ("admin", 403),
        ("admin-ccs-category", 403),
        ("admin-ccs-sourcing", 403),
        ("admin-framework-manager", 200),
        ("admin-manager", 403),
    ])
    def test_buyer_csv_is_only_accessible_to_specific_user_roles(self, data_api_client, role, expected_code):
        self.user_role = role
        data_api_client.find_users_iter.return_value = [
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
