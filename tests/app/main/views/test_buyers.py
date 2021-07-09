import mock
import pytest
from dmapiclient import HTTPError
from lxml import html

from ...helpers import LoggedInApplicationTest, Response


class TestBuyersView(LoggedInApplicationTest):

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.buyers.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()

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
    def test_find_buyers_page_is_only_accessible_to_specific_user_roles(self, role, expected_code):
        self.user_role = role
        response = self.client.get('/admin/buyers?brief_id=1')
        actual_code = response.status_code
        assert actual_code == expected_code, "Unexpected response {} for role {}".format(actual_code, role)

    def test_should_show_find_buyers_page(self):
        self.data_api_client.get_brief.return_value = None
        response = self.client.get('admin/buyers')
        page_html = response.get_data(as_text=True)
        document = html.fromstring(page_html)
        heading = document.xpath(
            '//h1/text()')[0].strip()

        assert response.status_code == 200
        assert "There are no opportunities with ID" not in page_html
        assert heading == "Find a buyer"

    def test_should_be_a_404_if_no_brief_found(self):
        self.data_api_client.get_brief.side_effect = HTTPError(Response(status_code=404))
        response = self.client.get('admin/buyers?brief_id=1')

        assert response.status_code == 404

    def test_should_display_a_useful_message_if_no_brief_found(self):
        self.data_api_client.get_brief.side_effect = HTTPError(Response(status_code=404))
        response = self.client.get('admin/buyers?brief_id=1')

        document = html.fromstring(response.get_data(as_text=True))
        banner_message = document.xpath('//p[@class="banner-message"]//text()')[0].strip()

        assert banner_message == "There are no opportunities with ID 1"

    def test_brief_not_found_flash_message_injection(self):
        """
        Asserts that raw HTML in a bad brief ID cannot be injected into a flash message.
        """
        # impl copied from test_should_display_a_useful_message_if_no_brief_found
        self.data_api_client.get_brief.side_effect = HTTPError(Response(status_code=404))
        response = self.client.get('admin/buyers?brief_id=1%3Cimg%20src%3Da%20onerror%3Dalert%281%29%3E')
        assert response.status_code == 404

        html_response = response.get_data(as_text=True)
        assert "1<img src=a onerror=alert(1)>" not in html_response
        assert "1&lt;img src=a onerror=alert(1)&gt;" in html_response

    def test_table_should_show_a_useful_message_if_no_users(self):
        self.data_api_client.get_brief.return_value = {
            'briefs': {
                'title': 'No users in here',
                'users': list()
            }
        }
        response = self.client.get('admin/buyers?brief_id=1')

        document = html.fromstring(response.get_data(as_text=True))
        table_content = document.xpath('//p[@class="summary-item-no-content"]//text()')[0].strip()

        assert table_content == "No buyers to show"

    def test_should_show_brief_title(self):
        brief = self.load_example_listing("brief_response")
        self.data_api_client.get_brief.return_value = brief
        response = self.client.get('/admin/buyers?brief_id=1')

        document = html.fromstring(response.get_data(as_text=True))
        title = document.xpath('//h2[@class="summary-item-heading"]//text()')[0].strip()

        assert title == "Individual Specialist-Buyer Requirements"

    def test_should_show_buyers_contact_details(self):
        brief = self.load_example_listing("brief_response")
        self.data_api_client.get_brief.return_value = brief
        response = self.client.get('/admin/buyers?brief_id=1')

        document = html.fromstring(response.get_data(as_text=True))
        [name, email, phone] = [
            field.xpath("normalize-space(string())")
            for field in document.xpath('//td[@class="summary-item-field"]/span')
        ]

        assert name == "Test Buyer"
        assert email == "test_buyer@example.com"
        assert phone == "02078888888"


class TestAddBuyerDomainsView(LoggedInApplicationTest):

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.buyers.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    @pytest.mark.parametrize("role,expected_code", [
        ("admin", 200),
        ("admin-ccs-category", 200),
        ("admin-ccs-sourcing", 403),
        ("admin-ccs-data-controller", 403),
        ("admin-framework-manager", 403),
        ("admin-manager", 403),
    ])
    def test_get_page_should_only_be_accessible_to_specific_user_roles(self, role, expected_code):
        self.user_role = role
        response = self.client.get('/admin/buyers/add-buyer-domains')
        actual_code = response.status_code
        assert actual_code == expected_code, "Unexpected response {} for role {}".format(actual_code, role)

    @pytest.mark.parametrize("role,expected_code", [
        ("admin", 302),
        ("admin-ccs-category", 302),
        ("admin-ccs-sourcing", 403),
        ("admin-ccs-data-controller", 403),
        ("admin-framework-manager", 403),
        ("admin-manager", 403),
    ])
    def test_post_page_should_only_be_accessible_to_specific_user_roles(self, role, expected_code):
        self.user_role = role
        response = self.client.post('/admin/buyers/add-buyer-domains',
                                    data={
                                        'new_buyer_domain': 'something.org.uk',
                                    }
                                    )
        actual_code = response.status_code
        assert actual_code == expected_code, "Unexpected response {} for role {}".format(actual_code, role)

    @pytest.mark.parametrize("new_buyer_domain", (
        "kev.uk",
        "zz",
    ))
    def test_admin_user_can_add_a_new_buyer_domain(self, new_buyer_domain):
        response1 = self.client.post('/admin/buyers/add-buyer-domains',
                                     data={'new_buyer_domain': new_buyer_domain}
                                     )
        assert response1.status_code == 302
        self.assert_flashes(f"You’ve added {new_buyer_domain}.")
        assert self.data_api_client.create_buyer_email_domain.call_args_list == [
            mock.call(new_buyer_domain, "test@example.com")
        ]

        response2 = self.client.get(response1.location)
        assert f"You’ve added {new_buyer_domain}" in response2.get_data(as_text=True)

    def test_admin_user_cannot_add_blacklisted_buyer_domain(self):
        response = self.client.post(
            '/admin/buyers/add-buyer-domains',
            data={'new_buyer_domain': "org.uk"},
        )
        assert response.status_code == 400
        assert self.data_api_client.create_buyer_email_domain.called is False

        document = html.fromstring(response.get_data(as_text=True))

        assert document.xpath(
            "//*[@class='banner-message'][normalize-space(string())=$t]",
            t="Cannot use this domain suffix: ‘.org.uk’ domains are publicly purchasable",
        )

    def test_post_empty_form_error(self):
        response = self.client.post('/admin/buyers/add-buyer-domains',
                                    data={'new_buyer_domain': ''}
                                    )
        assert response.status_code == 400
        assert "The domain field can not be empty." in response.get_data(as_text=True)
        assert self.data_api_client.create_buyer_email_domain.call_args_list == []

    def test_post_duplicate_domain_error(self):
        mock_api_error = mock.Mock(status_code=400)
        mock_api_error.json.return_value = {"error": "Domain name already-exists.org has already been approved"}
        self.data_api_client.create_buyer_email_domain.side_effect = HTTPError(mock_api_error)
        response = self.client.post('/admin/buyers/add-buyer-domains',
                                    data={'new_buyer_domain': 'already-exists.org'}
                                    )
        assert response.status_code == 400
        assert "You cannot add this domain because it already exists." in response.get_data(as_text=True)
        assert self.data_api_client.create_buyer_email_domain.call_args_list == [
            mock.call("already-exists.org", "test@example.com")]

    def test_post_bad_domain_error(self):
        mock_api_error = mock.Mock(status_code=400)
        mock_api_error.json.return_value = {"error": "JSON was not a valid format: 'inv@lid.co' does not match..."}
        self.data_api_client.create_buyer_email_domain.side_effect = HTTPError(mock_api_error)
        response = self.client.post('/admin/buyers/add-buyer-domains',
                                    data={'new_buyer_domain': 'inv@lid.co'}
                                    )
        assert response.status_code == 400
        assert "‘inv@lid.co’ is not a valid format" in response.get_data(as_text=True)
        assert self.data_api_client.create_buyer_email_domain.call_args_list == [
            mock.call("inv@lid.co", "test@example.com")
        ]

    def test_unexpected_api_error_falls_back_to_default_error_page(self):
        mock_api_error = mock.Mock(status_code=418)
        mock_api_error.json.return_value = {"error": "Something happened that we don't understand"}
        self.data_api_client.create_buyer_email_domain.side_effect = HTTPError(mock_api_error)
        response = self.client.post('/admin/buyers/add-buyer-domains',
                                    data={'new_buyer_domain': 'coffee.gov'}
                                    )
        assert response.status_code == 500
        assert "Sorry, we’re experiencing technical difficulties" in response.get_data(as_text=True)
        assert self.data_api_client.create_buyer_email_domain.call_args_list == [
            mock.call("coffee.gov", "test@example.com")
        ]
