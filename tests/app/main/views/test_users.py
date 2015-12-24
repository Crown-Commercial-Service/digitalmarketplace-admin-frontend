# coding=utf-8
from __future__ import unicode_literals

try:
    from urlparse import urlsplit
    from StringIO import StringIO
except ImportError:
    from urllib.parse import urlsplit
    from io import BytesIO as StringIO
import mock
import copy
import six
from lxml import html
from ...helpers import LoggedInApplicationTest


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
        self.assertEquals('/admin/suppliers/users?supplier_id=1000', supplier_link.attrib['href'])

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
        return self.client.get('/admin/users/export')

    def _assert_things_about_frameworks(self, response, frameworks):

        def _assert_things_about_valid_frameworks(options, frameworks):
            valid_frameworks = [
                framework for framework in frameworks if framework['status'] not in self._bad_statuses]

            assert len(options) == len(valid_frameworks)
            for framework in valid_frameworks:
                assert framework['slug'] in [option.xpath('input')[0].attrib['value'] for option in options]
                assert framework['name'] in ["".join(option.xpath('text()')).strip() for option in options]

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

    def _return_post_user_export_response(self, data_api_client, frameworks, users, framework_slug=None):
        # collection of users is modified in the route
        data_api_client.export_users.return_value = {"users": copy.copy(users)}
        data_api_client.find_frameworks.return_value = {"frameworks": frameworks}

        if framework_slug is None:
            framework_slug = frameworks[0]['slug']

        return self.client.post(
            '/admin/users/export',
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

    def test_get_form_with_invalid_framework(self, data_api_client):
        frameworks = [self._invalid_framework]
        response = self._return_get_user_export_response(data_api_client, frameworks)
        assert self.strip_all_whitespace("No valid frameworks were found.") in \
            self.strip_all_whitespace(response.get_data(as_text=True))
        assert response.status_code == 200
        self._assert_things_about_frameworks(response, frameworks)

    def test_get_form_with_valid_and_framework(self, data_api_client):
        frameworks = [self._valid_framework, self._invalid_framework]
        response = self._return_get_user_export_response(data_api_client, frameworks)
        assert response.status_code == 200
        self._assert_things_about_frameworks(response, frameworks)

    def test_post_user_export_with_no_users(self, data_api_client):
        frameworks = [self._valid_framework]
        users = []

        response = self._return_post_user_export_response(data_api_client, frameworks, users)
        assert response.status_code == 200
        self._assert_things_about_user_export(response, users)

    def test_post_user_export_with_one_user(self, data_api_client):
        frameworks = [self._valid_framework]
        users = [{
            "application_result": "fail",
            "application_status": "no_application",
            "declaration_status": "unstarted",
            "framework_agreement": False,
            "supplier_id": 1,
            "user_email": "test.user@sme.com",
            "user_name": "Tess User"
        }]

        response = self._return_post_user_export_response(data_api_client, frameworks, users)
        assert response.status_code == 200
        self._assert_things_about_user_export(response, users)

    def test_post_user_export_with_two_users(self, data_api_client):
        frameworks = [self._valid_framework]
        users = [{
            "application_result": 'fail',
            "application_status": '汉字$@!%^%&^*%&^	 	 	',
            "declaration_status": 'chữ Nôm',
            "framework_agreement": False,
            "supplier_id": 1,
            "user_email": 'test.user@sme.com',
            "user_name": 'Tess User'
        }, {
            "application_result": 'pass',
            "application_status": 'application',
            "declaration_status": 'complete',
            "framework_agreement": False,
            "supplier_id": 2,
            "user_email": 'paul@paul.paul',
            "user_name": 'Paul'
        }]

        response = self._return_post_user_export_response(data_api_client, frameworks, users)
        assert response.status_code == 200
        self._assert_things_about_user_export(response, users)

    def test_cannot_post_user_export_with_no_framework(self, data_api_client):
        frameworks = [self._valid_framework]
        framework_slug = ''
        users = []
        response = self._return_post_user_export_response(data_api_client, frameworks, users, framework_slug)
        assert response.status_code == 400
        assert self.strip_all_whitespace("A list of users can&#39;t be generated unless you select a valid framework") in \
            self.strip_all_whitespace(response.get_data(as_text=True))

    def test_cannot_post_user_export_with_bad_framework_slug(self, data_api_client):
        frameworks = [self._valid_framework]
        framework_slug = 'all-the-frameworks-in-the-uk'
        users = []
        response = self._return_post_user_export_response(data_api_client, frameworks, users, framework_slug)
        assert response.status_code == 400
        assert self.strip_all_whitespace("A list of users can&#39;t be generated unless you select a valid framework") in \
            self.strip_all_whitespace(response.get_data(as_text=True))
