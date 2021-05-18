import pytest
from lxml import html

from ...helpers import LoggedInApplicationTest


class TestSearchSuppliersAndServices(LoggedInApplicationTest):

    @pytest.mark.parametrize("role, expected_header", [
        ("admin", "Edit supplier accounts or view services"),
        ("admin-ccs-category", "Edit suppliers and services"),
        ("admin-ccs-sourcing", "Edit supplier declarations"),
        ("admin-framework-manager", "View suppliers and services"),
    ])
    def test_should_show_search_suppliers_and_services_page_with_role_appropriate_header(self, role, expected_header):
        self.user_role = role
        response = self.client.get('/admin/search')
        page_html = response.get_data(as_text=True)
        document = html.fromstring(page_html)
        header = document.xpath(
            '///h1/text()')[0].strip()
        title = document.xpath('//title/text()')[0].strip()

        assert response.status_code == 200
        assert header == expected_header
        assert title.startswith(expected_header)

    @pytest.mark.parametrize("role,expected_code", [
        ("admin", 200),
        ("admin-ccs-category", 200),
        ("admin-ccs-sourcing", 200),
        ("admin-manager", 403),
        ("admin-framework-manager", 200),
        ("admin-ccs-data-controller", 200),
    ])
    def test_search_suppliers_and_services_is_only_accessible_to_specific_user_roles(
            self, role, expected_code
    ):
        self.user_role = role
        response = self.client.get('/admin/search')
        actual_code = response.status_code
        assert actual_code == expected_code, "Unexpected response {} for role {}".format(actual_code, role)

    @pytest.mark.parametrize(
        "role, supplier_name_form_should_exist, supplier_duns_form_should_exist, service_id_form_should_exist, "
        "company_reg_number_should_exist", [
            ("admin", True, True, True, True),
            ("admin-ccs-category", True, True, True, True),
            ("admin-ccs-sourcing", True, True, False, True),
            ("admin-framework-manager", True, True, True, True),
            ("admin-ccs-data-controller", True, True, False, True)
        ])
    def test_forms_visible_for_relevant_roles(
            self, role, supplier_name_form_should_exist, supplier_duns_form_should_exist, service_id_form_should_exist,
            company_reg_number_should_exist
    ):
        self.user_role = role
        response = self.client.get('/admin/search')
        document = html.fromstring(response.get_data(as_text=True))
        question_headings = [heading.strip() for heading in document.xpath('//span[@class="question-heading"]/text()')]

        # We test that we can find the relevant question headings as a proxy for finding the forms themselves
        assert len(question_headings) == (
            supplier_name_form_should_exist + supplier_duns_form_should_exist + service_id_form_should_exist +
            company_reg_number_should_exist
        )
        assert ("Find a supplier by name" in question_headings) is supplier_name_form_should_exist, (
            "Role {} {} see the Find-by-name form".format(role, "can not" if supplier_name_form_should_exist else "can")
        )
        assert ("Find a supplier by DUNS number" in question_headings) is supplier_duns_form_should_exist, (
            "Role {} {} see the Find-by-DUNS form".format(role, "can not" if supplier_duns_form_should_exist else "can")
        )
        assert ("Find a service by service ID" in question_headings) is service_id_form_should_exist, (
            "Role {} {} see the Find-by-ID form".format(role, "can not" if service_id_form_should_exist else "can")
        )
        assert ("Find a supplier by company registration number" in question_headings) is \
            company_reg_number_should_exist, (
            "Role {} {} see the Find-by-company-registration form".format(role, "can not" if
                                                                          company_reg_number_should_exist else "can")
        )
