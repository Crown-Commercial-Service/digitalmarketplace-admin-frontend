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
        ("admin-ccs-data-controller", 403),
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
        assert last_login_day == 'Thursday 23 July 2015'

        last_password_changed = document.xpath(
            '//tr[@class="summary-item-row"]//td/span/text()')[5].strip()
        assert last_password_changed == '12:46:01'

        last_password_changed_day = document.xpath(
            '//tr[@class="summary-item-row"]//td/span/text()')[6].strip()
        assert last_password_changed_day == 'Monday 29 June 2015'

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
            '//input[@class="button-destructive"]')[0].attrib['value']
        deactivate_link = document.xpath(
            '//tr[@class="summary-item-row"]//td/span/form')[0]
        return_link = document.xpath(
            '//tr[@class="summary-item-row"]//td/span/form/input')[1]
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

        assert document.xpath('//input[@value="Activate"][@type="submit"]')


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

    @pytest.mark.parametrize(
        ('slug_suffix', 'name_suffix', 'should_be_shown'),
        (
            ('', '', False),
            ('-2', ' 2', True),
            ('-3', ' 3', False),
        )
    )
    def test_dos2_framework_only_expired_framework_available(self, s3, slug_suffix, name_suffix, should_be_shown):
        self.data_api_client.get_framework.return_value = FrameworkStub(
            status='expired',
            slug=f'digital-outcomes-and-specialists{slug_suffix}',
            name=f'Digital Outcomes and Specialists{name_suffix}',
        ).single_result_response()

        response = self.client.get(f"/admin/frameworks/{slug_suffix}/users")
        document = html.fromstring(response.get_data(as_text=True))

        if should_be_shown:
            page_heading = document.xpath(
                '//h1//text()')[0].strip()
            assert page_heading == f"Download supplier lists for Digital Outcomes and Specialists{name_suffix}"
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

    def test_dos2_framework_only_expired_framework_available(self, s3):
        framework_suffixes = (('', ''), ('-2', ' 2'), ('-3', ' 3'))
        self.data_api_client.find_frameworks.return_value = {
            'frameworks': [
                FrameworkStub(
                    status='expired',
                    slug=f'digital-outcomes-and-specialists{suffixes[0]}',
                    name=f'Digital Outcomes and Specialists{suffixes[1]}',
                ).response() for suffixes in framework_suffixes
            ]
        }
        s3.S3.return_value.get_signed_url.return_value = 'http://asseturl/path/to/csv?querystring'

        response = self.client.get('/admin/users/download/suppliers')
        assert response.status_code == 200

        document = html.fromstring(response.get_data(as_text=True))
        links = document.xpath("//a[@class='document-link-with-icon']")

        assert len(links) == 1  # Invalid frameworks not shown
        assert 'User research participants on Digital Outcomes and Specialists 2' in links[0].text_content()

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
