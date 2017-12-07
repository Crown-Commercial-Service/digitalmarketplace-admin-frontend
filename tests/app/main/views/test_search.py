import mock
import pytest
from dmapiclient import HTTPError
from lxml import html

from tests.app.main.helpers.flash_tester import assert_flashes
from ...helpers import LoggedInApplicationTest, Response


@mock.patch('app.main.views.buyers.data_api_client')
class TestSearchView(LoggedInApplicationTest):
    @pytest.mark.parametrize("role,expected_code", [
        ("admin", 200),
        ("admin-ccs-category", 200),
        ("admin-ccs-sourcing", 200),
        ("admin-manager", 403),
        ("admin-framework-manager", 200),
    ])
    def test_find_suppliers_and_services_page_is_only_accessible_to_specific_user_roles(
        self, data_api_client, role, expected_code
    ):
        self.user_role = role
        response = self.client.get('/admin/find-suppliers-and-services')
        actual_code = response.status_code
        assert actual_code == expected_code, "Unexpected response {} for role {}".format(actual_code, role)

    def test_should_show_find_suppliers_and_services_page(self, data_api_client):
        response = self.client.get('/admin/find-suppliers-and-services')
        page_html = response.get_data(as_text=True)
        document = html.fromstring(page_html)
        heading = document.xpath(
            '//header[@class="page-heading page-heading-without-breadcrumb"]//h1/text()')[0].strip()

        assert response.status_code == 200
        assert heading == "Find suppliers and services"
