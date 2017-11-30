# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import copy
from datetime import datetime

import mock
import pytest
import six
from dmapiclient import HTTPError
from lxml import html

from app.main.views.users import CLOSED_BRIEF_STATUSES
from ...helpers import LoggedInApplicationTest


@mock.patch('app.main.views.users.data_api_client')
class TestUsersView(LoggedInApplicationTest):
    @pytest.mark.parametrize("role,expected_code", [
        ("admin", 200),
        ("admin-ccs-category", 200),
        ("admin-ccs-sourcing", 403),
        ("admin-manager", 403),
    ])
    def test_find_users_page_is_only_accessible_to_specific_user_roles(self, data_api_client, role, expected_code):
        self.user_role = role
        data_api_client.get_user.return_value = self.load_example_listing("user_response")
        response = self.client.get('/admin/users?email_address=some@email.com')
        actual_code = response.status_code
        assert actual_code == expected_code, "Unexpected response {} for role {}".format(actual_code, role)

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

    def test_should_be_a_404_if_no_email_param_provided(self, data_api_client):
        data_api_client.get_user.return_value = None
        response = self.client.get('/admin/users')
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

        email_address = document.xpath(
            '//header[@class="page-heading page-heading-without-breadcrumb"]//h1/text()')[0].strip()
        assert email_address == "test.user@sme.com"

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

        email_address = document.xpath(
            '//header[@class="page-heading page-heading-without-breadcrumb"]//h1/text()')[0].strip()
        assert email_address == "test.user@sme.com"

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
class TestUsersExport(LoggedInApplicationTest):
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

    def _return_user_export_response(self, data_api_client, framework, users, framework_slug=None):
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
            '/admin/users/download/<_valid_framework',
            data={'framework_slug': framework_slug}
        )

    def _assert_things_about_user_export(self, response, users):

        rows = [line.split(",") for line in response.get_data(as_text=True).splitlines()]

        assert len(rows) == len(users) + 1

        if users:
            assert sorted(list(users[0].keys())) == sorted(rows[0])

            for index, user in enumerate(users):
                assert sorted([six.text_type(val) for val in user.values()]) == sorted(rows[index + 1])

    ##########################################################################
    def test_get_form_with_valid_framework(self, data_api_client):
        self.user_role = 'admin-framework-manager'
        frameworks = [self._valid_framework]
        response = self._return_get_user_export_response(data_api_client, frameworks)
        assert response.status_code == 200
        self._assert_things_about_frameworks(response, frameworks)

    def test_user_export_with_one_user(self, data_api_client):
        framework = self._valid_framework
        users = [{
            "application_result": "fail",
            "application_status": "no_application",
            "declaration_status": "unstarted",
            "framework_agreement": False,
            "supplier_id": 1,
            "email address": "test.user@sme.com",
            "user_name": "Test User",
            "variations_agreed": "var1"
        }]

        response = self._return_user_export_response(data_api_client, framework, users)
        assert response.status_code == 200

    def test_download_csv(self, data_api_client):
        framework = self._valid_framework
        users = [{
            "application_result": "fail",
            "application_status": "no_application",
            "declaration_status": "unstarted",
            "framework_agreement": False,
            "supplier_id": 1,
            "email address": "test.user@sme.com",
            "user_name": "Test User",
            "variations_agreed": "var1"
        }]

        response = self._return_user_export_response(data_api_client, framework, users)
        assert response.status_code == 200
        self._assert_things_about_user_export(response, users)


@mock.patch('app.main.views.users.data_api_client')
class TestBuyersExport(LoggedInApplicationTest):

    def test_response_data_has_buyer_info(self, data_api_client):
        data_api_client.find_users_iter.return_value = [
            {
                'id': 1,
                "name": "Chris",
                "emailAddress": "chris@gov.uk",
                "phoneNumber": "01234567891",
                "createdAt": "2016-08-04T12:00:00.000000Z",
            }
        ]

        data_api_client.find_briefs_iter.return_value = [
            {
                'id': 321,
                'title': 'This is a brief',
                'status': 'draft',
                'users': [{
                    'id': 1
                }],
                "location": "Wales",
                "lotSlug": "magic-roundabout",
            }
        ]

        response = self.client.get('/admin/users/download/buyers')

        assert response.status_code == 200

        rows = [line.split(",") for line in response.get_data(as_text=True).splitlines()]
        assert len(rows) == 2

        header = rows[0]
        buyer = rows[1]

        assert header == [
            u'user.name',
            u'user.emailAddress',
            u'user.phoneNumber',
            u'user.createdAtDate',

            u'brief.id',
            u'brief.title',
            u'brief.location',
            u'brief.lotSlug',
            u'brief.status',
            u'brief.applicationsClosedAtDateIfClosed',
        ]
        assert buyer == [
            u'Chris', u'chris@gov.uk', u'01234567891', u'2016-08-04',
            u'321', u'This is a brief', u'Wales', u'magic-roundabout', u'draft', u'',
        ]

    def test_response_has_two_lines_for_buyer_if_multiple_briefs(self, data_api_client):
        data_api_client.find_users_iter.return_value = [
            {
                'id': 1,
                "name": "Chris",
                "emailAddress": "chris@gov.uk",
                "phoneNumber": "01234567891",
                "createdAt": "2016-08-04T12:00:00.000000Z",
            },
        ]

        data_api_client.find_briefs_iter.return_value = [
            {
                'id': 321,
                'title': 'This is a brief',
                'status': 'draft',
                'location': 'Wales',
                'users': [{
                    'id': 1
                }],
                'lotSlug': 'magic-roundabout',
            },
            {
                'id': 432,
                'title': 'This is a second brief',
                'status': 'draft',
                'users': [{
                    'id': 1
                }],
                'lotSlug': 'manege-enchante',
            },
        ]

        response = self.client.get('/admin/users/download/buyers')

        assert response.status_code == 200

        rows = [line.split(",") for line in response.get_data(as_text=True).splitlines()]
        buyer_briefs = rows[1:]

        assert buyer_briefs == [
            [
                u'Chris', u'chris@gov.uk', u'01234567891', u'2016-08-04',
                u'321', u'This is a brief', u'Wales', u'magic-roundabout', u'draft', u'',
            ],
            [
                u'Chris', u'chris@gov.uk', u'01234567891', u'2016-08-04',
                u'432', u'This is a second brief', u'', u'manege-enchante', u'draft', u'',
            ],
        ]

    def test_buyer_is_listed_if_they_have_no_briefs(self, data_api_client):
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

        assert response.status_code == 200

        rows = [line.split(",") for line in response.get_data(as_text=True).splitlines()]
        buyer_briefs = rows[1:]

        assert buyer_briefs == [
            [
                u'Chris', u'chris@gov.uk', u'01234567891', u'2016-08-04',
                u'', u'', u'', u'', u'', u'',
            ],
        ]

    def test_multiple_buyers_are_assigned_correct_briefs(self, data_api_client):
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

        data_api_client.find_briefs_iter.return_value = [
            {
                'id': 321,
                'title': 'This is a brief',
                'location': 'London',
                'status': 'draft',
                'users': [{
                    'id': 1
                }],
                'lotSlug': 'magic-roundabout',
            },
            {
                'id': 432,
                'title': 'This is a second brief',
                'location': 'Wales',
                'status': 'draft',
                'users': [{
                    'id': 2
                }],
                'lotSlug': 'manege-enchante',
            }
        ]

        response = self.client.get('/admin/users/download/buyers')
        assert response.status_code == 200

        rows = [line.split(",") for line in response.get_data(as_text=True).splitlines()]
        buyer_briefs = rows[1:]

        assert buyer_briefs == [
            [
                u'Chris', u'chris@gov.uk', u'01234567891', u'2016-08-04',
                u'321', u'This is a brief', u'London', u'magic-roundabout', u'draft', u'',
            ],
            [
                u'Topher', u'topher@gov.uk', u'01234567891', u'2016-08-05',
                u'432', u'This is a second brief', u'Wales', u'manege-enchante', u'draft', u'',
            ],
        ]

    def test_mutiple_buyers_are_assigned_same_brief_if_they_are_users(self, data_api_client):
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

        data_api_client.find_briefs_iter.return_value = [
            {
                'id': 321,
                'title': 'This is a brief',
                'status': 'draft',
                'location': 'Wales',
                'users': [
                    {
                        'id': 1
                    },
                    {
                        'id': 2
                    }
                ],
                'lotSlug': 'magic-roundabout',
            }
        ]

        response = self.client.get('/admin/users/download/buyers')

        assert response.status_code == 200

        rows = [line.split(",") for line in response.get_data(as_text=True).splitlines()]
        buyer_briefs = rows[1:]

        assert buyer_briefs == [
            [
                u'Chris', u'chris@gov.uk', u'01234567891', u'2016-08-04',
                u'321', u'This is a brief', u'Wales', u'magic-roundabout', u'draft', u'',
            ],
            [
                u'Topher', u'topher@gov.uk', u'01234567891', u'2016-08-05',
                u'321', u'This is a brief', u'Wales', u'magic-roundabout', u'draft', u'',
            ],
        ]

    def test_brief_status_is_output_as_open_instead_of_live(self, data_api_client):
        data_api_client.find_users_iter.return_value = [
            {
                'id': 1,
                "name": "Chris",
                "emailAddress": "chris@gov.uk",
                "phoneNumber": "01234567891",
                "createdAt": "2016-08-04T12:00:00.000000Z",
            }
        ]

        data_api_client.find_briefs_iter.return_value = [
            {
                'id': 321,
                'title': 'This is a brief',
                'location': 'London',
                'status': 'live',
                'users': [{
                    'id': 1
                }],
                "applicationsClosedAt": "2016-09-05T12:00:00.000000Z",
                'lotSlug': 'magic-roundabout',
            }
        ]

        response = self.client.get('/admin/users/download/buyers')

        assert response.status_code == 200

        rows = [line.split(",") for line in response.get_data(as_text=True).splitlines()]
        buyer = rows[1]

        assert buyer[4:] == [u"321", u"This is a brief", u"London", u'magic-roundabout', u"open", u"", ]

    @pytest.mark.parametrize("status", CLOSED_BRIEF_STATUSES)
    def test_brief_applications_closed_at_is_output_if_brief_status_is_closed_or_awarded(self, data_api_client, status):
        data_api_client.find_users_iter.return_value = [
            {
                'id': 1,
                "name": "Chris",
                "emailAddress": "chris@gov.uk",
                "phoneNumber": "01234567891",
                "createdAt": "2016-08-04T12:00:00.000000Z",
            }
        ]

        data_api_client.find_briefs_iter.return_value = [
            {
                'id': 321,
                'title': 'This is a brief',
                'location': 'London',
                'status': status,
                'users': [{
                    'id': 1
                }],
                "applicationsClosedAt": "2016-09-05T12:00:00.000000Z",
                'lotSlug': 'magic-roundabout',
            }
        ]

        response = self.client.get('/admin/users/download/buyers')

        assert response.status_code == 200

        rows = [line.split(",") for line in response.get_data(as_text=True).splitlines()]
        buyer = rows[1]

        assert buyer[4:] == [u"321", u"This is a brief", u"London", u'magic-roundabout', status, u"2016-09-05", ]

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

        assert [row[0] for row in rows[1:5]] == ['Brian', 'Dougal', 'Florence', 'Zebedee']

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

        data_api_client.find_briefs_iter.return_value = [
            {
                'id': 321,
                'title': 'This is a brief',
                'status': 'draft',
                'users': [{
                    'id': 1
                }],
                'lotSlug': 'magic-roundabout',
            }
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

            data_api_client.find_briefs_iter.return_value = [
                {
                    'id': 321,
                    'title': 'This is a brief',
                    'status': 'draft',
                    'users': [{
                        'id': 1
                    }],
                    'lotSlug': 'magic-roundabout',
                }
            ]

            response = self.client.get('/admin/users/download/buyers')

            assert response.headers['Content-Disposition'] == 'attachment;filename=buyers_20160805T160000.csv'
