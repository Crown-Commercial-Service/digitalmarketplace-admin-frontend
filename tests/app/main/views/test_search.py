import pytest
from lxml import html

from ...helpers import LoggedInApplicationTest


class TestSearchView(LoggedInApplicationTest):
    @pytest.mark.parametrize("role,expected_code", [
        ("admin", 200),
        ("admin-ccs-category", 200),
        ("admin-ccs-sourcing", 200),
        ("admin-manager", 403),
        ("admin-framework-manager", 200),
    ])
    def test_find_suppliers_and_services_page_is_only_accessible_to_specific_user_roles(
        self, role, expected_code
    ):
        self.user_role = role
        response = self.client.get('/admin/find-suppliers-and-services')
        actual_code = response.status_code
        assert actual_code == expected_code, "Unexpected response {} for role {}".format(actual_code, role)

    def test_should_show_find_suppliers_and_services_page(self):
        response = self.client.get('/admin/find-suppliers-and-services')
        page_html = response.get_data(as_text=True)
        document = html.fromstring(page_html)
        heading = document.xpath(
            '//header[@class="page-heading page-heading-without-breadcrumb"]//h1/text()')[0].strip()

        assert response.status_code == 200
        assert heading == "Find suppliers and services"

    @pytest.mark.parametrize("role,form_1_exists,form_2_exists,form_3_exists", [
        ("admin", True, True, True),
        ("admin-ccs-category", True, True, True),
        ("admin-ccs-sourcing", True, True, False),
        ("admin-framework-manager", True, True, True),
    ])
    def test_forms_visible_for_relevant_roles(self, role, form_1_exists, form_2_exists, form_3_exists):
        self.user_role = role
        response = self.client.get('/admin/find-suppliers-and-services')
        document = html.fromstring(response.get_data(as_text=True))
        title_1_exists = bool(
            document.xpath('//span[@class="question-heading"][contains(text(),"Find a supplier by name")]')
        )
        title_2_exists = bool(
            document.xpath('//span[@class="question-heading"][contains(text(),"Find a supplier by DUNS number")]')
        )
        title_3_exists = bool(
            document.xpath('//span[@class="question-heading"][contains(text(),"Find a service by service ID")]')
        )
        assert title_1_exists == form_1_exists, (
            "Role {} {} see the Find a supplier by name form".format(role, "can not" if form_1_exists else "can")
        )
        assert title_2_exists == form_2_exists, (
            "Role {} {} see the Find a supplier by DUNS number form".format(role, "can not" if form_2_exists else "can")
        )
        assert title_3_exists == form_3_exists, (
            "Role {} {} see the Find a service by service ID form".format(role, "can not" if form_3_exists else "can")
        )
