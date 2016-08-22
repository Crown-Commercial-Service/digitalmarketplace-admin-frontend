# coding=utf-8
from __future__ import unicode_literals
from datetime import datetime

import mock
import copy
import six
from lxml import html
from ...helpers import LoggedInApplicationTest
from dmapiclient import HTTPError


@mock.patch('app.main.views.users.data_api_client')
class TestUsersView(LoggedInApplicationTest):

    def test_should_be_a_404_if_user_not_found(self, data_api_client):
        data_api_client.get_user.return_value = None
        response = self.client.get('/admin/users?email_address=some@email.com')
        self.assertEquals(response.status_code, 404)

        document = html.fromstring(response.get_data(as_text=True))

        page_title = document.xpath(
            '//p[@class="banner-message"]//text()')[0].strip()
        self.assertEqual("Sorry, we couldn't find an account with that email address", page_title)

        page_title = document.xpath(
            '//p[@class="summary-item-no-content"]//text()')[0].strip()
        self.assertEqual("No users to show", page_title)

    def test_should_be_a_404_if_no_email_provided(self, data_api_client):
        data_api_client.get_user.return_value = None
        response = self.client.get('/admin/users?email_address=')
        self.assertEquals(response.status_code, 404)

        document = html.fromstring(response.get_data(as_text=True))

        page_title = document.xpath(
            '//p[@class="banner-message"]//text()')[0].strip()
        self.assertEqual("Sorry, we couldn't find an account with that email address", page_title)

        page_title = document.xpath(
            '//p[@class="summary-item-no-content"]//text()')[0].strip()
        self.assertEqual("No users to show", page_title)

    def test_should_be_a_404_if_no_email_param_provided(self, data_api_client):
        data_api_client.get_user.return_value = None
        response = self.client.get('/admin/users')
        self.assertEquals(response.status_code, 404)

        document = html.fromstring(response.get_data(as_text=True))

        page_title = document.xpath(
            '//p[@class="banner-message"]//text()')[0].strip()
        self.assertEqual("Sorry, we couldn't find an account with that email address", page_title)

        page_title = document.xpath(
            '//p[@class="summary-item-no-content"]//text()')[0].strip()
        self.assertEqual("No users to show", page_title)

    def test_should_show_buyer_user(self, data_api_client):
        buyer = self.load_example_listing("user_response")
        buyer.pop('supplier', None)
        buyer['users']['role'] = 'buyer'
        data_api_client.get_user.return_value = buyer
        response = self.client.get('/admin/users?email_address=test.user@sme.com')
        self.assertEquals(response.status_code, 200)

        document = html.fromstring(response.get_data(as_text=True))

        email_address = document.xpath(
            '//header[@class="page-heading page-heading-without-breadcrumb"]//h1/text()')[0].strip()
        self.assertEqual("test.user@sme.com", email_address)

        name = document.xpath(
            '//tr[@class="summary-item-row"]//td/span/text()')[0].strip()
        self.assertEqual("Test User", name)

        role = document.xpath(
            '//tr[@class="summary-item-row"]//td/span/text()')[1].strip()
        self.assertEqual("buyer", role)

        supplier = document.xpath(
            '//tr[@class="summary-item-row"]//td/span/text()')[2].strip()
        self.assertEquals('', supplier)

        last_login = document.xpath(
            '//tr[@class="summary-item-row"]//td/span/text()')[3].strip()
        self.assertEquals('10:33:53', last_login)

        last_login_day = document.xpath(
            '//tr[@class="summary-item-row"]//td/span/text()')[4].strip()
        self.assertEquals('23 July', last_login_day)

        last_password_changed = document.xpath(
            '//tr[@class="summary-item-row"]//td/span/text()')[5].strip()
        self.assertEquals('13:46:01', last_password_changed)

        last_password_changed_day = document.xpath(
            '//tr[@class="summary-item-row"]//td/span/text()')[6].strip()
        self.assertEquals('29 June', last_password_changed_day)

        locked = document.xpath(
            '//tr[@class="summary-item-row"]//td/span/text()')[7].strip()
        self.assertEquals('No', locked)

        button = document.xpath(
            '//input[@class="button-destructive"]')[0].value
        self.assertEquals('Deactivate', button)

    def test_should_show_supplier_user(self, data_api_client):
        buyer = self.load_example_listing("user_response")
        data_api_client.get_user.return_value = buyer
        response = self.client.get('/admin/users?email_address=test.user@sme.com')
        self.assertEquals(response.status_code, 200)

        document = html.fromstring(response.get_data(as_text=True))

        email_address = document.xpath(
            '//header[@class="page-heading page-heading-without-breadcrumb"]//h1/text()')[0].strip()
        self.assertEqual("test.user@sme.com", email_address)

        role = document.xpath(
            '//tr[@class="summary-item-row"]//td/span/text()')[1].strip()
        self.assertEqual("supplier", role)

        supplier = document.xpath(
            '//tr[@class="summary-item-row"]//td/span/a/text()')[0].strip()
        self.assertEquals('SME Corp UK Limited', supplier)

        supplier_link = document.xpath(
            '//tr[@class="summary-item-row"]//td/span/a')[0]
        self.assertEquals('/admin/suppliers?supplier_id=1000', supplier_link.attrib['href'])

    def test_should_show_unlock_button(self, data_api_client):
        buyer = self.load_example_listing("user_response")
        buyer['users']['locked'] = True

        data_api_client.get_user.return_value = buyer
        response = self.client.get('/admin/users?email_address=test.user@sme.com')
        self.assertEquals(response.status_code, 200)

        document = html.fromstring(response.get_data(as_text=True))

        unlock_button = document.xpath(
            '//input[@class="button-secondary"]')[0].attrib['value']
        unlock_link = document.xpath(
            '//tr[@class="summary-item-row"]//td/span/form')[0]
        return_link = document.xpath(
            '//tr[@class="summary-item-row"]//td/span/form/input')[1]
        self.assertEquals('/admin/suppliers/users/999/unlock', unlock_link.attrib['action'])
        self.assertEquals('Unlock', unlock_button)
        self.assertEquals('/admin/users?email_address=test.user%40sme.com', return_link.attrib['value'])

    def test_should_show_deactivate_button(self, data_api_client):
        buyer = self.load_example_listing("user_response")

        data_api_client.get_user.return_value = buyer
        response = self.client.get('/admin/users?email_address=test.user@sme.com')
        self.assertEquals(response.status_code, 200)

        document = html.fromstring(response.get_data(as_text=True))

        deactivate_button = document.xpath(
            '//input[@class="button-destructive"]')[0].attrib['value']
        deactivate_link = document.xpath(
            '//tr[@class="summary-item-row"]//td/span/form')[0]
        return_link = document.xpath(
            '//tr[@class="summary-item-row"]//td/span/form/input')[1]
        self.assertEquals('/admin/suppliers/users/999/deactivate', deactivate_link.attrib['action'])
        self.assertEquals('Deactivate', deactivate_button)
        self.assertEquals('/admin/users?email_address=test.user%40sme.com', return_link.attrib['value'])


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
                assert sorted([six.text_type(val) for val in user.values()]) == sorted(rows[index+1])

    ##########################################################################
    def test_get_form_with_valid_framework(self, data_api_client):
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
            "user_email": "test.user@sme.com",
            "user_name": "Tess User"
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
            "user_email": "test.user@sme.com",
            "user_name": "Tess User"
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
                "createdAt": "Thu, 04 Aug 2016 12:00:00 GMT"
            }
        ]

        data_api_client.find_briefs_iter.return_value = [
            {
                'title': 'This is a brief',
                'status': 'draft',
                'users': [{
                    'id': 1
                }]
            }
        ]

        response = self.client.get('/admin/users/download/buyers')
        rows = [line.split(",") for line in response.get_data(as_text=True).splitlines()]
        header = rows[0]
        buyer = rows[1]

        assert response.status_code == 200
        assert header == [u'name', u'emailAddress', u'phoneNumber', u'createdAt', u'briefs']
        assert buyer == [u'Chris', u'chris@gov.uk', u'01234567891',
                         u'"Thu', u' 04 Aug 2016 12:00:00 GMT"', u'This is a brief - draft']

    def test_response_has_only_one_line_for_buyer_if_multiple_briefs(self, data_api_client):
        data_api_client.find_users_iter.return_value = [
            {
                'id': 1,
                "name": "Chris",
                "emailAddress": "chris@gov.uk",
                "phoneNumber": "01234567891",
                "createdAt": "Thu, 04 Aug 2016 12:00:00 GMT"
            }
        ]

        data_api_client.find_briefs_iter.return_value = [
            {
                'title': 'This is a brief',
                'status': 'draft',
                'users': [{
                    'id': 1
                }]
            },
            {
                'title': 'This is a second brief',
                'status': 'draft',
                'users': [{
                    'id': 1
                }]
            }
        ]

        response = self.client.get('/admin/users/download/buyers')
        rows = [line.split(",") for line in response.get_data(as_text=True).splitlines()]
        buyer = rows[1]

        assert response.status_code == 200
        assert len(rows) == 2
        assert buyer == [u'Chris', u'chris@gov.uk', u'01234567891', u'"Thu',
                         u' 04 Aug 2016 12:00:00 GMT"',
                         u'This is a brief - draft; This is a second brief - draft']

    def test_buyer_is_listed_if_they_have_no_briefs(self, data_api_client):
        data_api_client.find_users_iter.return_value = [
            {
                'id': 1,
                "name": "Chris",
                "emailAddress": "chris@gov.uk",
                "phoneNumber": "01234567891",
                "createdAt": "Thu, 04 Aug 2016 12:00:00 GMT"
            }
        ]

        response = self.client.get('/admin/users/download/buyers')
        rows = [line.split(",") for line in response.get_data(as_text=True).splitlines()]
        buyer = rows[1]

        assert response.status_code == 200
        assert buyer == [u'Chris', u'chris@gov.uk', u'01234567891', u'"Thu',
                         u' 04 Aug 2016 12:00:00 GMT"', '']

    def test_multiple_buyers_are_assigned_correct_briefs(self, data_api_client):
        data_api_client.find_users_iter.return_value = [
            {
                'id': 1,
                "name": "Chris",
                "emailAddress": "chris@gov.uk",
                "phoneNumber": "01234567891",
                "createdAt": "Thu, 04 Aug 2016 12:00:00 GMT"
            },
            {
                'id': 2,
                "name": "Topher",
                "emailAddress": "topher@gov.uk",
                "phoneNumber": "01234567891",
                "createdAt": "Fri, 05 Aug 2016 12:00:00 GMT"
            }
        ]

        data_api_client.find_briefs_iter.return_value = [
            {
                'title': 'This is a brief',
                'status': 'draft',
                'users': [{
                    'id': 1
                }]
            },
            {
                'title': 'This is a second brief',
                'status': 'draft',
                'users': [{
                    'id': 2
                }]
            }
        ]

        response = self.client.get('/admin/users/download/buyers')
        rows = [line.split(",") for line in response.get_data(as_text=True).splitlines()]
        buyer_one = rows[1]
        buyer_two = rows[2]

        assert buyer_one == [u'Chris', u'chris@gov.uk', u'01234567891', u'"Thu',
                             u' 04 Aug 2016 12:00:00 GMT"', u'This is a brief - draft']
        assert buyer_two == [u'Topher', u'topher@gov.uk', u'01234567891', u'"Fri',
                             u' 05 Aug 2016 12:00:00 GMT"', u'This is a second brief - draft']

    def test_mutiple_buyers_are_assigned_same_brief_if_they_are_users(self, data_api_client):
        data_api_client.find_users_iter.return_value = [
            {
                'id': 1,
                "name": "Chris",
                "emailAddress": "chris@gov.uk",
                "phoneNumber": "01234567891",
                "createdAt": "Thu, 04 Aug 2016 12:00:00 GMT"
            },
            {
                'id': 2,
                "name": "Topher",
                "emailAddress": "topher@gov.uk",
                "phoneNumber": "01234567891",
                "createdAt": "Fri, 05 Aug 2016 12:00:00 GMT"
            }
        ]

        data_api_client.find_briefs_iter.return_value = [
            {
                'title': 'This is a brief',
                'status': 'draft',
                'users': [
                    {
                        'id': 1
                    },
                    {
                        'id': 2
                    }
                ]
            }
        ]

        response = self.client.get('/admin/users/download/buyers')
        rows = [line.split(",") for line in response.get_data(as_text=True).splitlines()]
        buyer_one = rows[1]
        buyer_two = rows[2]

        assert buyer_one == [u'Chris', u'chris@gov.uk', u'01234567891', u'"Thu',
                             u' 04 Aug 2016 12:00:00 GMT"', u'This is a brief - draft']
        assert buyer_two == [u'Topher', u'topher@gov.uk', u'01234567891', u'"Fri',
                             u' 05 Aug 2016 12:00:00 GMT"', u'This is a brief - draft']

    def test_brief_status_is_output_as_open_instead_of_live(self, data_api_client):
        data_api_client.find_users_iter.return_value = [
            {
                'id': 1,
                "name": "Chris",
                "emailAddress": "chris@gov.uk",
                "phoneNumber": "01234567891",
                "createdAt": "Thu, 04 Aug 2016 12:00:00 GMT"
            }
        ]

        data_api_client.find_briefs_iter.return_value = [
            {
                'title': 'This is a brief',
                'status': 'live',
                'users': [{
                    'id': 1
                }]
            }
        ]

        response = self.client.get('/admin/users/download/buyers')
        rows = [line.split(",") for line in response.get_data(as_text=True).splitlines()]
        buyer = rows[1]

        assert buyer[5] == u'This is a brief - open'

    def test_csv_is_sorted_by_name(self, data_api_client):
        data_api_client.find_users_iter.return_value = [
            {
                'id': 1,
                "name": "Zebedee",
                "emailAddress": "zebedee@gov.uk",
                "phoneNumber": "01234567891",
                "createdAt": "Thu, 04 Aug 2016 12:00:00 GMT"
            },
            {
                'id': 2,
                "name": "Dougal",
                "emailAddress": "dougal@gov.uk",
                "phoneNumber": "01234567891",
                "createdAt": "Fri, 05 Aug 2016 12:00:00 GMT"
            },
            {
                'id': 3,
                "name": "Brian",
                "emailAddress": "brian@gov.uk",
                "phoneNumber": "01234567891",
                "createdAt": "Sat, 06 Aug 2016 12:00:00 GMT"
            },
            {
                'id': 4,
                "name": "Florence",
                "emailAddress": "florence@gov.uk",
                "phoneNumber": "01234567891",
                "createdAt": "Sun, 07 Aug 2016 12:00:00 GMT"
            }
        ]

        response = self.client.get('/admin/users/download/buyers')
        rows = [line.split(",") for line in response.get_data(as_text=True).splitlines()]

        assert rows[1][0] == 'Brian'
        assert rows[2][0] == 'Dougal'
        assert rows[3][0] == 'Florence'
        assert rows[4][0] == 'Zebedee'

    def test_response_is_a_csv(self, data_api_client):
        data_api_client.find_users_iter.return_value = [
            {
                'id': 1,
                "name": "Chris",
                "emailAddress": "chris@gov.uk",
                "phoneNumber": "01234567891",
                "createdAt": "Thu, 04 Aug 2016 12:00:00 GMT"
            }
        ]

        data_api_client.find_briefs_iter.return_value = [
            {
                'title': 'This is a brief',
                'status': 'draft',
                'users': [{
                    'id': 1
                }]
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
                    "createdAt": "Thu, 04 Aug 2016 12:00:00 GMT"
                }
            ]

            data_api_client.find_briefs_iter.return_value = [
                {
                    'title': 'This is a brief',
                    'status': 'draft',
                    'users': [{
                        'id': 1
                    }]
                }
            ]

            response = self.client.get('/admin/users/download/buyers')

            assert response.headers['Content-Disposition'] == 'attachment;filename=buyers_20160805T160000.csv'
