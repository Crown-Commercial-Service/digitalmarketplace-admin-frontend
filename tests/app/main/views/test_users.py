# -*- coding: utf-8 -*-
import mock
import pytest
from lxml import html
from dmtestutils.api_model_stubs import FrameworkStub
from freezegun import freeze_time

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
        ("admin-ccs-data-controller", 200),
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
            '//h1/text()')[0].strip()

        assert response.status_code == 200
        assert "Sorry, we couldn't find an account with that email address" not in page_html
        assert heading == "Find a user"

    def test_should_be_a_404_if_user_not_found(self):
        self.data_api_client.get_user.return_value = None
        response = self.client.get('/admin/users?email_address=some@email.com')
        assert response.status_code == 404

        document = html.fromstring(response.get_data(as_text=True))

        flash_message = "Sorry, we couldn't find an account with that email address"
        assert len(document.cssselect(f'.banner-message:contains("{flash_message}")')) == 1

        summary_result = "No users to show"
        assert len(document.cssselect(f'.govuk-body:contains("{summary_result}")')) == 1

    def test_should_be_a_404_if_no_email_provided(self):
        self.data_api_client.get_user.return_value = None
        response = self.client.get('/admin/users?email_address=')
        assert response.status_code == 404

        document = html.fromstring(response.get_data(as_text=True))

        flash_message = "Sorry, we couldn't find an account with that email address"
        assert len(document.cssselect(f'.banner-message:contains("{flash_message}")')) == 1

        summary_result = "No users to show"
        assert len(document.cssselect(f'.govuk-body:contains("{summary_result}")')) == 1

    def test_should_show_buyer_user(self):
        buyer = self.load_example_listing("user_response")
        buyer.pop('supplier', None)
        buyer['users']['role'] = 'buyer'
        self.data_api_client.get_user.return_value = buyer
        response = self.client.get('/admin/users?email_address=test.user@sme.com')
        assert response.status_code == 200

        document = html.fromstring(response.get_data(as_text=True))

        name = document.xpath(
            '//tr[@class="govuk-table__row"]//td/text()')[0].strip()
        assert name == "Test User"

        role = document.xpath(
            '//tr[@class="govuk-table__row"]//td/text()')[1].strip()
        assert role == "buyer"

        supplier = document.xpath(
            '//tr[@class="govuk-table__row"]//td/text()')[2].strip()
        assert supplier == ''

        last_login = document.xpath(
            '//tr[@class="govuk-table__row"]//td/text()')[3].strip()
        assert last_login == '09:33:53'

        last_login_day = document.xpath(
            '//tr[@class="govuk-table__row"]//td/text()')[4].strip()
        assert last_login_day == 'Thursday 23 July 2015'

        last_password_changed = document.xpath(
            '//tr[@class="govuk-table__row"]//td/text()')[5].strip()
        assert last_password_changed == '12:46:01'

        last_password_changed_day = document.xpath(
            '//tr[@class="govuk-table__row"]//td/text()')[6].strip()
        assert last_password_changed_day == 'Monday 29 June 2015'

        locked = document.xpath(
            '//tr[@class="govuk-table__row"]//td/text()')[7].strip()
        assert locked == 'No'

        button = document.xpath(
            '//button[contains(@class, "govuk-button--warning")]')[0].text.strip()
        assert button == 'Deactivate'

    def test_should_show_supplier_user(self):
        response = self.client.get('/admin/users?email_address=test.user@sme.com')
        assert response.status_code == 200

        document = html.fromstring(response.get_data(as_text=True))

        role = document.xpath(
            '//tr[@class="govuk-table__row"]//td/text()')[1].strip()
        assert role == "supplier"

        supplier = document.xpath(
            '//tr[@class="govuk-table__row"]//td/a/text()')[0].strip()
        assert supplier == 'SME Corp UK Limited'

        supplier_link = document.xpath(
            '//tr[@class="govuk-table__row"]//td/a')[0]
        assert supplier_link.attrib['href'] == '/admin/suppliers?supplier_id=1000'

    def test_should_show_unlock_button(self):
        buyer = self.load_example_listing("user_response")
        buyer['users']['locked'] = True

        self.data_api_client.get_user.return_value = buyer
        response = self.client.get('/admin/users?email_address=test.user@sme.com')
        assert response.status_code == 200

        document = html.fromstring(response.get_data(as_text=True))

        unlock_button = document.xpath(
            '//button[contains(@class, "govuk-button--secondary")]')[0].text.strip()
        unlock_link = document.xpath(
            '//tr[@class="govuk-table__row"]//td/form')[0]
        return_link = document.xpath(
            '//tr[@class="govuk-table__row"]//td/form/input')[1]
        assert unlock_link.attrib['action'] == '/admin/suppliers/users/999/unlock'
        assert unlock_button == 'Unlock'
        assert return_link.attrib['value'] == '/admin/users?email_address=test.user%40sme.com'

    def test_should_not_show_unlock_button_if_user_personal_data_removed(self):
        buyer = self.load_example_listing("user_response")
        buyer['users'].update({'locked': True, 'personalDataRemoved': True})
        self.data_api_client.get_user.return_value = buyer

        response = self.client.get('/admin/users?email_address=test.user@sme.com')
        document = html.fromstring(response.get_data(as_text=True))

        assert not document.xpath('//input[@value="Unlock"][@type="submit"]')

    def test_should_show_deactivate_button(self):
        response = self.client.get('/admin/users?email_address=test.user@sme.com')
        assert response.status_code == 200

        document = html.fromstring(response.get_data(as_text=True))

        deactivate_button = document.xpath(
            '//button[contains(@class, "govuk-button--warning")]')[0].text.strip()
        deactivate_link = document.xpath(
            '//tr[@class="govuk-table__row"]//td/form')[0]
        return_link = document.xpath(
            '//tr[@class="govuk-table__row"]//td/form/input')[1]
        assert deactivate_link.attrib['action'] == '/admin/suppliers/users/999/deactivate'
        assert deactivate_button == 'Deactivate'
        assert return_link.attrib['value'] == '/admin/users?email_address=test.user%40sme.com'

    def test_should_not_show_deactivate_button_if_user_deactivated(self):
        buyer = self.load_example_listing("user_response")
        buyer['users'].update({'active': False})
        self.data_api_client.get_user.return_value = buyer

        response = self.client.get('/admin/users?email_address=test.user@sme.com')
        document = html.fromstring(response.get_data(as_text=True))

        assert not document.xpath('//input[@value="Deactivate"][@type="submit"]')

    def test_should_show_activate_button_if_user_deactivated_and_not_personal_data_removed(self):
        buyer = self.load_example_listing("user_response")
        buyer['users'].update({'active': False, 'personalDataRemoved': False})
        self.data_api_client.get_user.return_value = buyer

        response = self.client.get('/admin/users?email_address=test.user@sme.com')
        document = html.fromstring(response.get_data(as_text=True))

        assert document.xpath('//button[contains(text(), "Activate")]')


@mock.patch('app.main.views.users.s3')
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
        ("admin-ccs-category", 200),
        ("admin-ccs-sourcing", 403),
        ("admin-framework-manager", 200),
        ("admin-manager", 403),
        ("admin-ccs-data-controller", 200),
    ])
    def test_get_user_lists_is_only_accessible_to_specific_user_roles(self, s3, role, expected_code):
        self.user_role = role

        response = self.client.get("/admin/frameworks/g-cloud-9/users")
        actual_code = response.status_code
        assert actual_code == expected_code, "Unexpected response {} for role {}".format(actual_code, role)

    def test_get_user_lists_shows_framework_name_in_heading(self, s3):
        self.data_api_client.get_framework.return_value = {"frameworks": self._framework}
        self.app.config['DM_ASSETS_URL'] = 'http://example.com'

        response = self.client.get("/admin/frameworks/g-cloud-9/users")
        document = html.fromstring(response.get_data(as_text=True))

        page_heading = document.xpath(
            '//h1//text()')[0].strip()
        assert page_heading == "Download supplier lists for G-Cloud 9"

    @pytest.mark.parametrize('family,should_be_shown', (
        ('g-cloud', False),
        ('digital-outcomes-and-specialists', True),
    ))
    def test_dos_frameworks_only_expired_frameworks_available(self, s3, family, should_be_shown):
        self.data_api_client.get_framework.return_value = FrameworkStub(
            family=family,
            status='expired',
            slug=f'sunt-me-gratis-12',
            name=f'Sunt Me Gratis 12',
        ).single_result_response()

        response = self.client.get(f"/admin/frameworks/sunt-me-gratis-12/users")

        assert self.data_api_client.mock_calls == [
            mock.call.get_framework("sunt-me-gratis-12")
        ]

        if should_be_shown:
            assert response.status_code == 200
            document = html.fromstring(response.get_data(as_text=True))
            page_heading = document.xpath('normalize-space(string(//h1))')
            assert page_heading == f"Download supplier lists for Sunt Me Gratis 12"
        else:
            assert response.status_code == 404

    @mock.patch('app.main.views.users.get_signed_url')
    def test_download_supplier_user_account_list_report_redirects_to_s3_url(self, get_signed_url, s3):
        get_signed_url.return_value = 'http://path/to/csv?querystring'
        self.app.config['DM_ASSETS_URL'] = 'http://example.com'

        response = self.client.get("/admin/frameworks/g-cloud-9/users/accounts/download")
        assert response.status_code == 302

        assert get_signed_url.call_args_list == [
            mock.call(
                s3.S3.return_value,
                'g-cloud-9/reports/all-email-accounts-for-suppliers-g-cloud-9.csv',
                'http://example.com'
            ),
        ]

    @mock.patch('app.main.views.users.get_signed_url')
    def test_download_supplier_official_details_list_report_redirects_to_s3_url(self, get_signed_url, s3):
        get_signed_url.return_value = 'http://path/to/csv?querystring'
        self.app.config['DM_ASSETS_URL'] = 'http://example.com'

        response = self.client.get("/admin/frameworks/g-cloud-9/users/official/download")
        assert response.status_code == 302

        assert get_signed_url.call_args_list == [
            mock.call(
                s3.S3.return_value,
                'g-cloud-9/reports/official-details-for-suppliers-g-cloud-9.csv',
                'http://example.com'
            ),
        ]


@mock.patch('app.main.views.users.s3')
class TestUserResearchParticipantsExport(LoggedInApplicationTest):
    user_role = 'admin-framework-manager'

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

        self.data_api_client.find_users_iter.return_value = [
            {'id': 1, 'userResearchOptedIn': True, 'emailAddress': 'shania@example.com', 'name': "Shania Twain"},
            {'id': 2, 'userResearchOptedIn': False, 'emailAddress': 'mariah@example.com', 'name': "Mariah Carey"},
        ]

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    @pytest.mark.parametrize(
        ('role', 'status_code'),
        (
            ('admin', 403),
            ('admin-ccs-category', 403),
            ('admin-ccs-sourcing', 403),
            ('admin-manager', 403),
            ('admin-framework-manager', 200),
            ('admin-ccs-data-controller', 403),
        )
    )
    def test_correct_role_can_download_list_of_all_buyers(self, s3, role, status_code):
        self.user_role = role

        with freeze_time('2019-01-01'):
            response = self.client.get('/admin/users/download/buyers')

        assert response.status_code == status_code

    def test_download_list_of_all_buyers_includes_all_buyers(self, s3):
        with freeze_time('2019-01-01'):
            response = self.client.get('/admin/users/download/buyers')

        assert response.mimetype == 'text/csv'
        assert response.headers['Content-Disposition'] == "attachment;filename=all-buyers-on-2019-01-01-at-00-00-00.csv"
        assert response.headers['Content-Type'] == "text/csv; charset=utf-8"
        # Assert each line separately to avoid weird line break stuff
        assert 'email address,name' in response.get_data(as_text=True)
        assert 'shania@example.com,Shania Twain' in response.get_data(as_text=True)
        assert 'mariah@example.com,Mariah Carey' in response.get_data(as_text=True)
        self.data_api_client.find_users_iter.assert_called_once_with(role='buyer')

    @pytest.mark.parametrize(
        ('role', 'status_code'),
        (
            ('admin', 403),
            ('admin-ccs-category', 403),
            ('admin-ccs-sourcing', 403),
            ('admin-manager', 403),
            ('admin-framework-manager', 200),
            ('admin-ccs-data-controller', 403),
        )
    )
    def test_correct_role_can_download_list_of_buyer_user_research_participants(self, s3, role, status_code):
        self.user_role = role

        with freeze_time('2019-01-01'):
            response = self.client.get('/admin/users/download/buyers/user-research')
        assert response.status_code == status_code

    def test_download_list_of_all_buyer_user_research_partipants_filters_out_opted_out(self, s3):
        with freeze_time('2019-01-01'):
            response = self.client.get('/admin/users/download/buyers/user-research')

        assert response.mimetype == 'text/csv'
        assert response.headers['Content-Disposition'] == \
            "attachment;filename=user-research-buyers-on-2019-01-01-at-00-00-00.csv"
        assert response.headers['Content-Type'] == "text/csv; charset=utf-8"
        # Assert each line separately to avoid weird line break stuff
        assert 'email address,name' in response.get_data(as_text=True)
        assert 'shania@example.com,Shania Twain' in response.get_data(as_text=True)
        assert 'mariah@example.com,Mariah Carey' not in response.get_data(as_text=True)
        self.data_api_client.find_users_iter.assert_called_once_with(role='buyer')

    @pytest.mark.parametrize(
        ('role', 'status_code'),
        (
            ('admin', 403),
            ('admin-ccs-category', 403),
            ('admin-ccs-sourcing', 403),
            ('admin-manager', 403),
            ('admin-framework-manager', 200),
            ('admin-ccs-data-controller', 403),
        )
    )
    def test_correct_role_can_view_supplier_user_research_participants_page(self, s3, role, status_code):
        self.user_role = role

        response = self.client.get('/admin/users/download/suppliers')
        assert response.status_code == status_code

    def test_supplier_csvs_shown_for_valid_frameworks(self, s3):
        self.data_api_client.find_frameworks.return_value = {
            'frameworks': [self._valid_framework, self._invalid_framework]
        }
        s3.S3.return_value.get_signed_url.return_value = 'http://asseturl/path/to/csv?querystring'

        response = self.client.get('/admin/users/download/suppliers')
        assert response.status_code == 200

        text = response.get_data(as_text=True)
        document = html.fromstring(text)
        href_xpath = "//a[@class='document-link-with-icon']"

        assert len(document.xpath(href_xpath)) == 1  # Invalid framework not shown
        assert 'User research participants on {}'.format(self._valid_framework['name']) in text

    def test_dos_frameworks_only_expired_frameworks_available(self, s3):
        self.data_api_client.find_frameworks.return_value = {
            'frameworks': [
                FrameworkStub(
                    family='aliquid-alicui-bonum-vult',
                    status='expired',
                    slug='nulla-bona-2',
                    name='Nulla Bona 2',
                ).response(),
                FrameworkStub(
                    family='digital-outcomes-and-specialists',
                    status='expired',
                    slug='vere-dignum-13',
                    name='Vere Dignum 13',
                ).response(),
                FrameworkStub(
                    family='altius-aliquantulum',
                    status='expired',
                    slug='salvi-facti-sunt',
                    name='Salvi Facti Sunt',
                ).response(),
            ]
        }
        asset_url = 'http://asseturl/path/to/csv?querystring'
        s3.S3.return_value.get_signed_url.return_value = asset_url

        response = self.client.get('/admin/users/download/suppliers')
        assert response.status_code == 200

        document = html.fromstring(response.get_data(as_text=True))
        links = document.xpath("//a[@class='document-link-with-icon']")

        assert len(links) == 1  # Invalid frameworks not shown
        assert links[0].attrib["href"] == "/admin/frameworks/vere-dignum-13/user-research/download"
        assert 'User research participants on Vere Dignum 13' in links[0].xpath("normalize-space(string())")

    def test_supplier_csvs_shown_in_alphabetical_name_order(self, s3):
        framework_1 = self._valid_framework.copy()
        framework_2 = self._valid_framework.copy()
        framework_3 = self._valid_framework.copy()
        framework_1['name'] = 'aframework_1'
        framework_1['slug'] = 'a-fw-1'
        framework_2['name'] = 'bframework_1'
        framework_2['slug'] = 'b-fw-1'
        framework_3['name'] = 'bframework_2'
        framework_3['slug'] = 'b-fw-2'

        self.data_api_client.find_frameworks.return_value = {'frameworks': [framework_3, framework_1, framework_2]}

        response = self.client.get('/admin/users/download/suppliers')
        assert response.status_code == 200

        text = response.get_data(as_text=True)

        framework_1_link_text = 'User research participants on ' + framework_1['name']
        framework_2_link_text = 'User research participants on ' + framework_2['name']
        framework_3_link_text = 'User research participants on ' + framework_3['name']
        assert text.find(framework_1_link_text) < text.find(framework_2_link_text) < text.find(framework_3_link_text)

    @mock.patch('app.main.views.users.get_signed_url')
    def test_supplier_download_redirects_to_s3(self, get_signed_url, s3):
        get_signed_url.return_value = 'http://asseturl/path/to/csv?querystring'
        self.app.config['DM_ASSETS_URL'] = 'http://example.com'

        response = self.client.get('/admin/frameworks/g-cloud-9/user-research/download')
        assert response.status_code == 302

        assert get_signed_url.call_args_list == [
            mock.call(
                s3.S3.return_value,
                'g-cloud-9/reports/user-research-suppliers-on-g-cloud-9.csv',
                'http://example.com'
            ),
        ]
