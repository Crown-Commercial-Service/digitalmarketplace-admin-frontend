from io import BytesIO
from urllib.parse import urlparse, parse_qs

import mock
import pytest
from dmapiclient import HTTPError, APIError
from dmapiclient.audit import AuditTypes
from dmutils.email.exceptions import EmailError
from flask import current_app
from freezegun import freeze_time
from lxml import html

from dmtestutils.api_model_stubs import (
    FrameworkStub,
    SupplierStub,
    SupplierFrameworkStub,
)
from dmtestutils.fixtures import valid_pdf_bytes

from ...helpers import LoggedInApplicationTest, Response


class TestSupplierDetailsView(LoggedInApplicationTest):

    def setup_method(self, method):
        super().setup_method(method)
        self.user_role = "admin-ccs-data-controller"
        self.data_api_client_patch = mock.patch('app.main.views.suppliers.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()

        # common mock responses
        self.data_api_client.get_framework.side_effect = \
            lambda s: FrameworkStub(stub=s, status="live").single_result_response()

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    def test_get_returns_404_if_supplier_id_is_invalid(self):
        assert self.client.get("/admin/suppliers/invalid").status_code == 404
        assert self.client.get("/admin/suppliers/-1").status_code == 404
        self.data_api_client.get_supplier_frameworks.side_effect = HTTPError(Response(404))
        assert self.client.get("/admin/suppliers/0").status_code == 404
        self.data_api_client.get_supplier_frameworks.assert_called_with(0)

    def test_successful_for_supplier_with_no_frameworks(self):
        self.data_api_client.get_supplier_frameworks.return_value = {"frameworkInterest": []}
        assert self.client.get("/admin/suppliers/1234").status_code == 200

    @pytest.mark.parametrize(
        "role, expected_status_code", (
            ("admin", 200),
            ("admin-ccs-category", 200),
            ("admin-ccs-data-controller", 200),
            ("admin-ccs-sourcing", 200),
            ("admin-framework-manager", 200),
            ("admin-manager", 403),
        )
    )
    def test_is_shown_to_users_with_right_roles(self, role, expected_status_code):
        self.user_role = role
        status_code = self.client.get("/admin/suppliers/1234").status_code
        assert status_code == expected_status_code, "Unexpected response {} for role {}".format(status_code, role)

    @pytest.mark.parametrize(
        "role, link_should_be_visible", (
            ("admin", True),
            ("admin-ccs-category", True),
            ("admin-ccs-data-controller", True),
            ("admin-framework-manager", False),
            ("admin-ccs-sourcing", False)
        )
    )
    def test_edit_supplier_name_link_shown_to_users_with_right_roles(self, role, link_should_be_visible):
        self.user_role = role
        response = self.client.get("/admin/suppliers/1234")
        document = html.fromstring(response.get_data(as_text=True))

        expected_link_text = "Edit supplier name"
        expected_href = '/admin/suppliers/1234/edit/name'
        expected_link = document.xpath('.//a[contains(@href,"{}")]'.format(expected_href))

        link_is_visible = len(expected_link) > 0 and expected_link[0].text == expected_link_text

        assert link_is_visible is link_should_be_visible, (
            "Role {} {} see the link".format(role, "can not" if link_should_be_visible else "can")
        )

    @pytest.mark.parametrize(
        "role, link_should_be_visible", (
            ("admin", False),
            ("admin-ccs-category", False),
            ("admin-ccs-data-controller", True),
            ("admin-framework-manager", False),
            ("admin-ccs-sourcing", False)
        )
    )
    def test_edit_registered_details_links_shown_to_users_with_right_roles(self, role, link_should_be_visible):
        self.user_role = role
        self.data_api_client.get_supplier.return_value = SupplierStub(id=1234).single_result_response()

        response = self.client.get("/admin/suppliers/1234")
        document = html.fromstring(response.get_data(as_text=True))

        expected_hrefs = [
            '/admin/suppliers/1234/edit/registered-name',
            '/admin/suppliers/1234/edit/registered-company-number',
            '/admin/suppliers/1234/edit/duns-number',
            '/admin/suppliers/1234/edit/registered-address'

        ]
        for href in expected_hrefs:
            link_is_visible = len(document.xpath('.//a[contains(@href,"{}")]'.format(href))) > 0
            assert link_is_visible is link_should_be_visible, (
                "Role {} {} see the link".format(role, "can not" if link_should_be_visible else "can")
            )

    @mock.patch("app.main.views.suppliers.render_template", return_value="")
    def test_view_shows_company_details_from_suppliers_last_framework_declaration(self, render_template):
        framework_interest = SupplierFrameworkStub(framework_slug="g-cloud-11").response()
        framework_interest["declaration"]["supplierRegisteredPostcode"] = mock.sentinel.postcode

        self.data_api_client.find_frameworks.return_value = {'frameworks': [
            FrameworkStub(frameworkLiveAtUTC="a", status="live", slug="g-cloud-10").response(),
            FrameworkStub(frameworkLiveAtUTC="b", status="live", slug="g-cloud-11").response(),
            FrameworkStub(frameworkLiveAtUTC="c", status="live", slug="digital-outcomes-and-specialists-3").response(),
        ]}
        self.data_api_client.get_supplier_frameworks.return_value = {
            "frameworkInterest": [
                SupplierFrameworkStub(framework_slug="g-cloud-10").response(),
                SupplierFrameworkStub(framework_slug="digital-outcomes-and-specialists-3").response(),
                framework_interest,
            ]
        }

        self.client.get("/admin/suppliers/1234")
        company_details = render_template.call_args[1]["company_details"]
        assert (
            company_details["address"]["postcode"]
            ==
            mock.sentinel.postcode
        )

    @mock.patch("app.main.views.suppliers.render_template", return_value="")
    def test_if_no_declarations_show_account_company_details(self, render_template):
        self.data_api_client.get_supplier_frameworks.return_value = {
            "frameworkInterest": []
        }

        self.data_api_client.get_supplier.return_value = SupplierStub(
            companiesHouseNumber=mock.sentinel.registration_number,
            dunsNumber=mock.sentinel.duns_number,
            registeredName=mock.sentinel.registered_name,
            registrationCountry=mock.sentinel.country,
        ).single_result_response()

        self.client.get("/admin/suppliers/1234")
        company_details = render_template.call_args[1]["company_details"]
        assert company_details["address"]["country"] == mock.sentinel.country
        assert company_details["duns_number"] == mock.sentinel.duns_number
        assert company_details["registered_name"] == mock.sentinel.registered_name
        assert company_details["registration_number"] == mock.sentinel.registration_number

    @mock.patch("app.main.views.suppliers.render_template", return_value="")
    def test_if_most_recent_framework_has_no_declaration_show_account_company_details(self, render_template):
        self.data_api_client.get_supplier_frameworks.return_value = {
            "frameworkInterest": [
                SupplierFrameworkStub(framework_slug="g-cloud-6", declaration=None).response(),
            ]
        }

        self.data_api_client.get_supplier.return_value = {
            "suppliers": {
                "id": 1234,
                "name": "ABC",
                "dunsNumber": mock.sentinel.duns_number,
                "registrationCountry": "country:FR",
                "companiesHouseNumber": "12345678",
                "contactInformation": [
                    {
                        'id': 999,
                        'address1': '123 Rue Morgue',
                        'city': 'Paris',
                        'postcode': '76876',
                        'country': "not used"
                    }
                ]
            }
        }

        self.client.get("/admin/suppliers/1234")
        company_details = render_template.call_args[1]["company_details"]
        assert company_details == {
            "duns_number": mock.sentinel.duns_number,
            "registration_number": "12345678",
            "registered_name": None,
            "address": {
                'street_address_line_1': '123 Rue Morgue',
                'locality': 'Paris',
                'postcode': '76876',
                'country': "country:FR"
            }
        }

    @mock.patch("app.main.views.suppliers.render_template", return_value="")
    def test_if_most_recent_framework_has_old_declaration_show_account_company_details(self, render_template):
        self.data_api_client.get_supplier_frameworks.return_value = {
            "frameworkInterest": [
                SupplierFrameworkStub(
                    framework_slug="g-cloud-8",
                    declaration={
                        "dunsNumber": mock.sentinel.duns_number,
                        "currentRegisteredCountry": "country:FR",
                        "registeredVATNumber": "12345678",
                        "registeredAddressBuilding": "123 Rue Morgue",
                        "registeredAddressTown": "Paris",
                        "registeredAddressPostcode": "76876",
                    },
                ).response(),
            ]
        }

        self.data_api_client.get_supplier.return_value = {
            "suppliers": {
                "id": 1234,
                "name": "ABC",
                "dunsNumber": mock.sentinel.duns_number,
                "registrationCountry": "country:FR",
                "companiesHouseNumber": "12345678",
                "contactInformation": [
                    {
                        "id": 999,
                        "address1": "123 Rue Morgue",
                        "city": "Paris",
                        "postcode": "76876",
                        "country": "not used"
                    }
                ]
            }
        }

        self.client.get("/admin/suppliers/1234")
        company_details = render_template.call_args[1]["company_details"]
        assert company_details == {
            "duns_number": mock.sentinel.duns_number,
            "registration_number": "12345678",
            "registered_name": None,
            "address": {
                'street_address_line_1': '123 Rue Morgue',
                'locality': 'Paris',
                'postcode': '76876',
                'country': "country:FR"
            }
        }


class TestSupplierDetailsViewFrameworkTable(LoggedInApplicationTest):

    def setup_method(self, method):
        super().setup_method(method)
        self.user_role = "admin-ccs-data-controller"
        self.data_api_client_patch = mock.patch('app.main.views.suppliers.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()
        self.data_api_client.get_supplier_frameworks.return_value = {
            "frameworkInterest": [
                SupplierFrameworkStub(framework_slug="g-cloud-10").response(),
                SupplierFrameworkStub(framework_slug="digital-outcomes-and-specialists-3").response(),
                SupplierFrameworkStub(framework_slug="g-cloud-11").response(),
            ]
        }

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    @mock.patch("app.main.views.suppliers.render_template", return_value="")
    @pytest.mark.parametrize(
        "role, expected_visible_frameworks, expected_not_visible_frameworks", [
            (
                "admin-ccs-data-controller",
                ["digital-outcomes-and-specialists-3", "g-cloud-10"],
                ["g-cloud-11", "g-cloud-standstill-1", "g-cloud-pending-1", "g-cloud-open-1"]
            ),
            (
                "admin-ccs-sourcing",
                [
                    "g-cloud-10", "digital-outcomes-and-specialists-3", "g-cloud-standstill-1", "g-cloud-pending-1",
                    "g-cloud-open-1"
                ],
                ["g-cloud-coming-1"],
            )
        ]
    )
    def test_supplier_frameworks_includes_appropriate_frameworks_only(
        self, render_template, role, expected_visible_frameworks, expected_not_visible_frameworks
    ):
        self.user_role = role
        self.data_api_client.get_supplier_frameworks.return_value["frameworkInterest"].extend((
            SupplierFrameworkStub(framework_slug="g-cloud-standstill-1").response(),
            SupplierFrameworkStub(framework_slug="g-cloud-pending-1").response(),
            SupplierFrameworkStub(framework_slug="g-cloud-open-1").response(),
        ))

        self.data_api_client.find_frameworks.return_value = {'frameworks': [
            FrameworkStub(
                status="live",
                slug="g-cloud-10"
            ).response(),
            FrameworkStub(
                status="expired",
                slug="digital-outcomes-and-specialists-3"
            ).response(),
            FrameworkStub(
                status="coming",
                slug="g-cloud-11",
            ).response(),
            FrameworkStub(
                status="standstill",
                slug="g-cloud-standstill-1"
            ).response(),
            FrameworkStub(
                status="pending",
                slug="g-cloud-pending-1"
            ).response(),
            FrameworkStub(
                status="open",
                slug="g-cloud-open-1"
            ).response(),
            FrameworkStub(
                id=0,
                status="expired",
                slug="g-cloud-7"
            ).response(),
        ]}

        self.client.get("/admin/suppliers/1234")
        supplier_frameworks = render_template.call_args[1]["supplier_frameworks"]
        supplier_framework_slugs = [d["frameworkSlug"] for d in supplier_frameworks]

        assert set(expected_visible_frameworks) == set(supplier_framework_slugs)
        assert set(expected_not_visible_frameworks).isdisjoint(set(supplier_framework_slugs))

    @mock.patch("app.main.views.suppliers.render_template", return_value="")
    def test_supplier_frameworks_are_ordered_by_live_date(self, render_template):
        self.data_api_client.find_frameworks.return_value = {'frameworks': [
            FrameworkStub(
                frameworkLiveAtUTC="c",
                slug="g-cloud-10",
                status="live",
            ).response(),
            FrameworkStub(
                frameworkLiveAtUTC="a",
                slug="digital-outcomes-and-specialists-3",
                status="live",
            ).response(),
            FrameworkStub(
                frameworkLiveAtUTC="b",
                slug="g-cloud-11",
                status="live",
            ).response(),
            FrameworkStub(
                id=0,
                slug="g-cloud-7",
                status="expired"
            ).response(),
        ]}

        self.client.get("/admin/suppliers/1234")
        supplier_frameworks = render_template.call_args[1]["supplier_frameworks"]

        assert (
            [d["frameworkSlug"] for d in supplier_frameworks]
            ==
            [
                "digital-outcomes-and-specialists-3",
                "g-cloud-11",
                "g-cloud-10",
            ]
        )

    @pytest.mark.parametrize(
        "role, link_should_be_visible", (
            ("admin", False),
            ("admin-ccs-category", False),
            ("admin-ccs-data-controller", False),
            ("admin-framework-manager", False),
            ("admin-ccs-sourcing", True)
        )
    )
    def test_sourcing_admins_see_edit_declaration_link(self, role, link_should_be_visible):
        self.user_role = role
        self.data_api_client.find_frameworks.return_value = {'frameworks': [
            FrameworkStub(
                status="pending",
                slug="g-cloud-10"
            ).response()
        ]}

        response = self.client.get("/admin/suppliers/1234")
        document = html.fromstring(response.get_data(as_text=True))

        expected_link_text = "Edit declaration"
        expected_href = '/admin/suppliers/1234/edit/declarations/g-cloud-10'
        expected_link = document.xpath('.//a[contains(@href,"{}")]'.format(expected_href))

        link_is_visible = len(expected_link) > 0 and expected_link[0].text == expected_link_text

        assert link_is_visible is link_should_be_visible, (
            "Role {} {} see the link".format(role, "can not" if link_should_be_visible else "can")
        )


class TestSuppliersListView(LoggedInApplicationTest):

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.suppliers.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()
        self.data_api_client.find_frameworks.return_value = {
            'frameworks': [
                FrameworkStub(slug='g-cloud-7', name='G-Cloud 7', id=1).response(),
                FrameworkStub(slug='g-cloud-10', id=2).response()
            ]
        }
        self.data_api_client.find_suppliers.return_value = {
            "suppliers": [SupplierStub(id=12345).response()],
            "links": {"self": "http://localhost/suppliers"}
        }

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    @pytest.mark.parametrize("role,expected_code", [
        ("admin", 200),
        ("admin-ccs-category", 200),
        ("admin-ccs-sourcing", 200),
        ("admin-framework-manager", 200),
        ("admin-manager", 403),
    ])
    def test_supplier_list_is_shown_to_users_with_right_roles(self, role, expected_code):
        self.user_role = role
        response = self.client.get('/admin/suppliers?supplier_name=foo')
        actual_code = response.status_code
        assert actual_code == expected_code, "Unexpected response {} for role {}".format(actual_code, role)

    @pytest.mark.parametrize("role, link_should_be_visible", [
        ("admin", True),
        ("admin-ccs-category", True),
        ("admin-ccs-data-controller", True),
        ("admin-framework-manager", True),
        ("admin-ccs-sourcing", True),
        ("admin-manager", False),
    ])
    def test_details_link_is_shown_to_users_with_right_roles(self, role, link_should_be_visible):
        self.user_role = role
        response = self.client.get('/admin/suppliers?supplier_name=foo')

        document = html.fromstring(response.get_data(as_text=True))

        expected_link_text = "My Little Company"
        expected_href = '/admin/suppliers/12345'
        expected_link = document.xpath('.//a[contains(@href,"{}")]'.format(expected_href))

        link_is_visible = len(expected_link) > 0 and expected_link[0].text == expected_link_text

        assert link_is_visible is link_should_be_visible, (
            "Role {} {} see the link".format(role, "can not" if link_should_be_visible else "can")
        )

    @pytest.mark.parametrize(
        "link_text, href", [
            ("Users", "/admin/suppliers/users?supplier_id=1234"),
            ("Services", "/admin/suppliers/12345/services"),
        ]
    )
    @pytest.mark.parametrize(
        "role, link_should_be_visible", [
            ("admin", True),
            ("admin-ccs-category", True),
            ("admin-ccs-data-controller", True),
            ("admin-framework-manager", True),
            ("admin-ccs-sourcing", False)
        ]
    )
    def test_services_and_user_link_shown_to_users_with_right_roles(self, link_text, href, role,
                                                                    link_should_be_visible):
        self.user_role = role
        response = self.client.get('/admin/suppliers?supplier_name=foo')

        document = html.fromstring(response.get_data(as_text=True))

        expected_link = document.xpath('.//a[contains(@href,"{}")]'.format(href))

        link_is_visible = len(expected_link) > 0 and expected_link[0].text == link_text

        assert link_is_visible is link_should_be_visible, (
            "Role {} {} see the link".format(role, "can not" if link_should_be_visible else "can"))

    @mock.patch('app.main.views.suppliers.current_app')
    def test_should_500_if_no_framework_found_matching_the_oldest_interesting_defined(self, current_app):
        with mock.patch('app.main.views.suppliers.OLDEST_INTERESTING_FRAMEWORK_SLUG', new='not-a-framework'):
            response = self.client.get('/admin/suppliers')

        assert response.status_code == 500
        assert current_app.logger.error.call_args_list == [
            mock.call('No framework found with slug: "not-a-framework"')
        ]

    def test_should_raise_http_error_from_api(self):
        self.data_api_client.find_suppliers.side_effect = HTTPError(Response(404))
        response = self.client.get('/admin/suppliers')
        assert response.status_code == 404

    def test_should_list_suppliers_with_pagination(self):
        self.data_api_client.find_suppliers.return_value = {
            "suppliers": [
                SupplierStub(id=1234, name="Supplier 1").response(),
                SupplierStub(id=1235, name="Supplier 2").response()
            ],
            "links": {
                'prev': 'http://localhost/suppliers?page=1&name=foo',
                'self': 'http://localhost/suppliers?page=2&name=foo',
                'next': 'http://localhost/suppliers?page=3&name=foo',
                'last': 'http://localhost/suppliers?page=99&name=foo',
            }
        }
        self.data_api_client.get_supplier_framework_info.side_effect = [
            {"frameworkInterest": {"agreementPath": "path/the/first/1234-g7-agreement.pdf"}},
            {"frameworkInterest": {"agreementPath": None}},  # Supplier 1234 has not returned their DOS agreement yet
            HTTPError(Response(404)),                        # Supplier 1235 is not on G-Cloud 7
            {"frameworkInterest": {"agreementPath": "path/the/third/1235-dos-agreement.jpg"}},
        ]
        response = self.client.get("/admin/suppliers?supplier_name=foo&page=2")
        document = html.fromstring(response.get_data(as_text=True))

        assert response.status_code == 200
        assert len(document.cssselect('.summary-item-row')) == 2

        assert len(document.xpath("//a[normalize-space(string())='Previous page']")) == 1
        assert len(document.xpath("//a[normalize-space(string())='Next page']")) == 1

        prev_href = '/admin/suppliers?page=1&supplier_name=foo'
        assert len(document.xpath('.//a[contains(@href,"{}")]'.format(prev_href))) == 1
        next_href = '/admin/suppliers?page=3&supplier_name=foo'
        assert len(document.xpath('.//a[contains(@href,"{}")]'.format(next_href))) == 1

    def test_should_list_suppliers_with_no_pagination_for_single_page_of_results(self):
        self.data_api_client.find_suppliers.return_value = {
            "suppliers": [
                SupplierStub(id=1234, name="Supplier 1").response(),
                SupplierStub(id=1235, name="Supplier 2").response()
            ],
            "links": {
                'self': 'http://localhost/suppliers?name=foo',
            }
        }
        self.data_api_client.get_supplier_framework_info.side_effect = [
            {"frameworkInterest": {"agreementPath": "path/the/first/1234-g7-agreement.pdf"}},
        ]
        response = self.client.get("/admin/suppliers?supplier_name=foo")

        assert response.status_code == 200
        document = html.fromstring(response.get_data(as_text=True))
        assert len(document.xpath("//a[normalize-space(string())='Previous page']")) == 0
        assert len(document.xpath("//a[normalize-space(string())='Next page']")) == 0

    def test_should_search_by_prefix(self):
        self.data_api_client.find_suppliers.side_effect = HTTPError(Response(404))
        self.client.get("/admin/suppliers?supplier_name=foo")

        self.data_api_client.find_suppliers.assert_called_once_with(
            name="foo", duns_number=None, company_registration_number=None, page=1
        )

    def test_should_search_by_duns_number(self):
        self.data_api_client.find_suppliers.side_effect = HTTPError(Response(404))
        self.client.get("/admin/suppliers?supplier_duns_number=987654321")

        self.data_api_client.find_suppliers.assert_called_once_with(
            name=None, duns_number="987654321", company_registration_number=None, page=1
        )

    def test_should_search_by_company_registration_number(self):
        self.data_api_client.find_suppliers.side_effect = HTTPError(Response(404))
        self.client.get("/admin/suppliers?supplier_company_registration_number=11114444")

        self.data_api_client.find_suppliers.assert_called_once_with(
            name=None, duns_number=None, company_registration_number="11114444", page=1
        )

    def test_should_find_by_supplier_id(self):
        self.data_api_client.get_supplier.side_effect = HTTPError(Response(404))
        self.client.get("/admin/suppliers?supplier_id=12345")

        self.data_api_client.get_supplier.assert_called_once_with("12345")


class TestSupplierUsersView(LoggedInApplicationTest):

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.suppliers.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()
        self.data_api_client.get_supplier.return_value = self.load_example_listing("supplier_response")
        self.data_api_client.find_users_iter.return_value = self.load_example_listing("users_response")['users']

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    @pytest.mark.parametrize("role,expected_code", [
        ("admin", 200),
        ("admin-ccs-category", 200),
        ("admin-ccs-sourcing", 403),
        ("admin-ccs-data-controller", 200),
        ("admin-framework-manager", 200),
        ("admin-manager", 403),
    ])
    def test_supplier_users_accessible_to_users_with_right_roles(self, role, expected_code):
        self.user_role = role
        response = self.client.get('/admin/suppliers/users?supplier_id=1000')
        actual_code = response.status_code
        assert actual_code == expected_code, "Unexpected response {} for role {}".format(actual_code, role)

    @pytest.mark.parametrize("role, can_edit", [
        ("admin", True),
        ("admin-ccs-category", True),
        ("admin-framework-manager", False),
        ("admin-ccs-data-controller", False),
    ])
    def test_supplier_users_only_editable_for_users_with_right_roles(self, role, can_edit):
        self.user_role = role

        response = self.client.get('/admin/suppliers/users?supplier_id=1000')
        assert response.status_code == 200
        document = html.fromstring(response.get_data(as_text=True))
        deactivate_buttons = document.xpath('.//input[contains(@value, "Deactivate")]')
        assert len(deactivate_buttons) == (1 if can_edit else 0)

    def test_should_404_if_no_supplier_does_not_exist(self):
        self.data_api_client.get_supplier.side_effect = HTTPError(Response(404))
        response = self.client.get('/admin/suppliers/users?supplier_id=999')
        assert response.status_code == 404

    def test_should_404_if_no_supplier_id(self):
        response = self.client.get('/admin/suppliers/users')
        assert response.status_code == 404

    def test_should_call_apis_with_supplier_id(self):
        response = self.client.get('/admin/suppliers/users?supplier_id=1000')

        assert response.status_code == 200

        self.data_api_client.get_supplier.assert_called_once_with('1000')
        self.data_api_client.find_users_iter.assert_called_once_with('1000')

    def test_should_have_supplier_name_on_page(self):
        response = self.client.get('/admin/suppliers/users?supplier_id=1000')

        assert response.status_code == 200
        assert "Supplier Name" in response.get_data(as_text=True)

    def test_should_indicate_if_there_are_no_users(self):
        self.data_api_client.find_users_iter.return_value = {}

        response = self.client.get('/admin/suppliers/users?supplier_id=1000')

        assert response.status_code == 200
        assert "This supplier has no users on the Digital Marketplace" in response.get_data(as_text=True)

    def test_should_show_user_details_on_page(self):

        response = self.client.get('/admin/suppliers/users?supplier_id=1000')

        assert response.status_code == 200
        assert "Test User" in response.get_data(as_text=True)
        assert "test.user@sme.com" in response.get_data(as_text=True)
        assert "09:33:53" in response.get_data(as_text=True)
        assert "23 July" in response.get_data(as_text=True)
        assert "12:46:01" in response.get_data(as_text=True)
        assert "29 June" in response.get_data(as_text=True)
        assert "No" in response.get_data(as_text=True)

        document = html.fromstring(response.get_data(as_text=True))
        assert document.xpath('//input[@value="Deactivate"][@type="submit"][@class="button-destructive"]')
        assert document.xpath('//form[@action="/admin/suppliers/users/999/deactivate"][@method="post"]')
        assert document.xpath('//button[@class="button-save"][contains(text(), "Move user to this supplier")]')
        assert document.xpath('//form[@action="/admin/suppliers/1234/move-existing-user"][@method="post"]')

    def test_should_show_unlock_button_if_user_locked_and_not_personal_data_removed(self):
        users = self.load_example_listing("users_response")
        users["users"][0]["locked"] = True
        self.data_api_client.find_users_iter.return_value = users['users']

        response = self.client.get('/admin/suppliers/users?supplier_id=1000')

        assert response.status_code == 200

        document = html.fromstring(response.get_data(as_text=True))
        assert document.xpath('//form[@action="/admin/suppliers/users/999/unlock"][@method="post"]')
        assert document.xpath('//input[@value="Unlock"][@type="submit"][@class="button-secondary"]')

    def test_should_not_show_unlock_button_if_user_not_locked(self):
        users = self.load_example_listing("users_response")
        self.data_api_client.find_users_iter.return_value = users['users']

        response = self.client.get('/admin/suppliers/users?supplier_id=1000')

        assert response.status_code == 200

        document = html.fromstring(response.get_data(as_text=True))
        assert not document.xpath('//form[@action="/admin/suppliers/users/999/unlock"][@method="post"]')
        assert not document.xpath('//input[@value="Unlock"][@type="submit"][@class="button-secondary"]')

    def test_should_not_show_unlock_button_if_user_personal_data_removed(self):
        users = self.load_example_listing("users_response")
        users["users"][0]["personalDataRemoved"] = True
        self.data_api_client.find_users_iter.return_value = users['users']

        response = self.client.get('/admin/suppliers/users?supplier_id=1000')

        assert response.status_code == 200

        document = html.fromstring(response.get_data(as_text=True))
        assert not document.xpath('//form[@action="/admin/suppliers/users/999/unlock"][@method="post"]')
        assert not document.xpath('//input[@value="Unlock"][@type="submit"][@class="button-secondary"]')

    def test_should_show_activate_button_if_user_deactivated_and_not_personal_data_removed(self):
        users = self.load_example_listing("users_response")
        users["users"][0]["active"] = False
        self.data_api_client.find_users_iter.return_value = users['users']

        response = self.client.get('/admin/suppliers/users?supplier_id=1000')

        assert response.status_code == 200

        document = html.fromstring(response.get_data(as_text=True))
        assert document.xpath('//form[@action="/admin/suppliers/users/999/activate"][@method="post"]')
        assert document.xpath('//input[@value="Activate"][@type="submit"][@class="button-secondary"]')

    def test_should_not_show_activate_button_if_user_personal_data_removed(self):
        users = self.load_example_listing("users_response")
        users["users"][0]["personalDataRemoved"] = True
        self.data_api_client.find_users_iter.return_value = users['users']

        response = self.client.get('/admin/suppliers/users?supplier_id=1000')

        assert response.status_code == 200

        document = html.fromstring(response.get_data(as_text=True))

        assert not document.xpath('//form[@action="/admin/suppliers/users/999/activate"][@method="post"]')
        assert not document.xpath('//input[@value="Activate"][@type="submit"][@class="button-secondary"]')

    def test_should_not_show_activate_button_if_user_active(self):
        users = self.load_example_listing("users_response")
        self.data_api_client.find_users_iter.return_value = users['users']

        response = self.client.get('/admin/suppliers/users?supplier_id=1000')

        assert response.status_code == 200

        document = html.fromstring(response.get_data(as_text=True))

        assert not document.xpath('//form[@action="/admin/suppliers/users/999/activate"][@method="post"]')
        assert not document.xpath('//input[@value="Activate"][@type="submit"][@class="button-secondary"]')

    @pytest.mark.parametrize("role,expected_code", [
        ("admin", 302),
        ("admin-ccs-category", 302),
        ("admin-ccs-sourcing", 403),
        ("admin-ccs-data-controller", 403),
        ("admin-framework-manager", 403),
        ("admin-manager", 403),
    ])
    def test_unlock_users_accessible_to_users_with_right_roles(self, role, expected_code):
        self.user_role = role
        self.data_api_client.update_user.return_value = self.load_example_listing("user_response")

        response = self.client.post('/admin/suppliers/users/999/unlock')
        actual_code = response.status_code
        assert actual_code == expected_code, "Unexpected response {} for role {}".format(actual_code, role)

    def test_should_call_api_to_unlock_user(self):
        self.data_api_client.update_user.return_value = self.load_example_listing("user_response")

        response = self.client.post('/admin/suppliers/users/999/unlock')

        self.data_api_client.update_user.assert_called_once_with(999, locked=False, updater="test@example.com")

        assert response.status_code == 302
        assert response.location == "http://localhost/admin/suppliers/users?supplier_id=1000"

    @pytest.mark.parametrize("role,expected_code", [
        ("admin", 302),
        ("admin-ccs-category", 302),
        ("admin-ccs-sourcing", 403),
        ("admin-ccs-data-controller", 403),
        ("admin-framework-manager", 403),
        ("admin-manager", 403),
    ])
    def test_activate_users_accessible_to_users_with_right_roles(self, role, expected_code):
        self.user_role = role
        self.data_api_client.update_user.return_value = self.load_example_listing("user_response")

        response = self.client.post('/admin/suppliers/users/999/activate')
        actual_code = response.status_code
        assert actual_code == expected_code, "Unexpected response {} for role {}".format(actual_code, role)

    def test_should_call_api_to_activate_user(self):
        self.data_api_client.update_user.return_value = self.load_example_listing("user_response")

        response = self.client.post('/admin/suppliers/users/999/activate')

        self.data_api_client.update_user.assert_called_once_with(999, active=True, updater="test@example.com")

        assert response.status_code == 302
        assert response.location == "http://localhost/admin/suppliers/users?supplier_id=1000"

    def test_should_call_api_to_activate_user_and_redirect_to_source_if_present(self):
        self.data_api_client.update_user.return_value = self.load_example_listing("user_response")
        response = self.client.post(
            '/admin/suppliers/users/999/activate',
            data={'source': "http://example.com"}
        )

        self.data_api_client.update_user.assert_called_once_with(999, active=True, updater="test@example.com")

        assert response.status_code == 302
        assert response.location == "http://example.com"

    @pytest.mark.parametrize("role,expected_code", [
        ("admin", 302),
        ("admin-ccs-category", 302),
        ("admin-ccs-sourcing", 403),
        ("admin-ccs-data-controller", 403),
        ("admin-framework-manager", 403),
        ("admin-manager", 403),
    ])
    def test_deactivate_users_accessible_to_users_with_right_roles(self, role, expected_code):
        self.user_role = role
        self.data_api_client.update_user.return_value = self.load_example_listing("user_response")

        response = self.client.post('/admin/suppliers/users/999/deactivate')
        actual_code = response.status_code
        assert actual_code == expected_code, "Unexpected response {} for role {}".format(actual_code, role)

    def test_should_call_api_to_deactivate_user(self):
        self.data_api_client.update_user.return_value = self.load_example_listing("user_response")
        response = self.client.post(
            '/admin/suppliers/users/999/deactivate',
            data={'supplier_id': 1000}
        )

        self.data_api_client.update_user.assert_called_once_with(999, active=False, updater="test@example.com")

        assert response.status_code == 302
        assert response.location == "http://localhost/admin/suppliers/users?supplier_id=1000"

    def test_should_call_api_to_deactivate_user_and_redirect_to_source_if_present(self):
        response = self.client.post(
            '/admin/suppliers/users/999/deactivate',
            data={'supplier_id': 1000, 'source': "http://example.com"}
        )

        self.data_api_client.update_user.assert_called_once_with(999, active=False, updater="test@example.com")

        assert response.status_code == 302
        assert response.location == "http://example.com"

    @pytest.mark.parametrize("role,expected_code", [
        ("admin", 302),
        ("admin-ccs-category", 302),
        ("admin-ccs-sourcing", 403),
        ("admin-ccs-data-controller", 403),
        ("admin-framework-manager", 403),
        ("admin-manager", 403),
    ])
    def test_move_user_to_another_supplier_accessible_to_users_with_right_roles(self, role, expected_code):
        self.user_role = role
        self.data_api_client.get_user.return_value = self.load_example_listing("user_response")
        self.data_api_client.update_user.return_value = self.load_example_listing("user_response")

        response = self.client.post(
            '/admin/suppliers/1000/move-existing-user',
            data={'user_to_move_email_address': 'test.user@sme.com'}
        )
        actual_code = response.status_code
        assert actual_code == expected_code, "Unexpected response {} for role {}".format(actual_code, role)

    def test_should_call_api_to_move_user_to_another_supplier(self):
        self.data_api_client.get_user.return_value = self.load_example_listing("user_response")
        self.data_api_client.update_user.return_value = self.load_example_listing("user_response")

        response = self.client.post(
            '/admin/suppliers/1000/move-existing-user',
            data={'user_to_move_email_address': 'test.user@sme.com'}
        )

        self.data_api_client.update_user.assert_called_once_with(
            999, role='supplier', supplier_id=1000, active=True, updater="test@example.com"
        )

        assert response.status_code == 302
        assert response.location == "http://localhost/admin/suppliers/users?supplier_id=1000"


class TestSupplierServicesView(LoggedInApplicationTest):
    user_role = 'admin-ccs-category'

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.suppliers.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()

        self.data_api_client.get_supplier.return_value = self.load_example_listing("supplier_response")
        self.data_api_client.find_services.return_value = self.load_example_listing("services_response")
        self.data_api_client.find_frameworks.return_value = {
            'frameworks': [self.load_example_listing("framework_response")['frameworks']]
        }

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    @pytest.mark.parametrize("role, expected_code", [
        ("admin", 200),
        ("admin-ccs-category", 200),
        ("admin-ccs-sourcing", 403),
        ("admin-ccs-data-controller", 200),
        ("admin-framework-manager", 200),
        ("admin-manager", 403),
    ])
    def test_supplier_services_accessible_to_users_with_right_roles(self, role, expected_code):
        self.user_role = role

        response = self.client.get('/admin/suppliers/1000/services')
        actual_code = response.status_code
        assert actual_code == expected_code, "Unexpected response {} for role {}".format(actual_code, role)

    @pytest.mark.parametrize("role, can_edit", [
        ("admin", False),
        ("admin-ccs-category", True),
        ("admin-ccs-data-controller", False),
        ("admin-framework-manager", False),
    ])
    def test_supplier_services_only_category_users_can_edit(self, role, can_edit):
        self.user_role = role

        response = self.client.get('/admin/suppliers/1000/services')
        assert response.status_code == 200
        document = html.fromstring(response.get_data(as_text=True))
        remove_all_links = document.xpath('.//a[contains(text(), "Suspend services")]')
        assert len(remove_all_links) == (1 if can_edit else 0)
        edit_service_links = document.xpath('.//a[contains(text(), "Edit")]')
        assert len(edit_service_links) == (2 if can_edit else 0)
        view_service_links = document.xpath('.//a[contains(text(), "View")]')
        assert len(view_service_links) == (0 if can_edit else 2)

    @pytest.mark.parametrize("role, can_edit", [
        ("admin", False),
        ("admin-ccs-category", True),
        ("admin-ccs-data-controller", False),
        ("admin-framework-manager", False),
    ])
    def test_only_category_users_can_unsuspend_all_services(self, role, can_edit):
        self.user_role = role
        service = self.load_example_listing("services_response")["services"][0]
        service["status"] = "disabled"
        self.data_api_client.find_services.return_value = {'services': [service]}

        response = self.client.get('/admin/suppliers/1000/services')
        assert response.status_code == 200
        document = html.fromstring(response.get_data(as_text=True))
        unsuspend_all_links = document.xpath('.//a[contains(text(), "Unsuspend services")]')
        assert len(unsuspend_all_links) == (1 if can_edit else 0)

    def test_should_404_if_supplier_does_not_exist_on_services(self):
        self.data_api_client.get_supplier.side_effect = HTTPError(Response(404))
        response = self.client.get('/admin/suppliers/999/services')
        assert response.status_code == 404

    def test_should_404_if_no_supplier_id_on_services(self):
        response = self.client.get('/admin/suppliers/services')
        assert response.status_code == 404

    def test_should_call_service_apis_with_supplier_id(self):
        response = self.client.get('/admin/suppliers/1000/services')

        assert response.status_code == 200

        self.data_api_client.get_supplier.assert_called_once_with(1000)
        assert self.data_api_client.find_services.call_args_list == [
            mock.call(framework='g-cloud-8', supplier_id=1000)
        ]

    def test_should_indicate_if_supplier_has_no_services(self):
        self.data_api_client.find_services.return_value = {'services': []}
        response = self.client.get('/admin/suppliers/1000/services')

        assert response.status_code == 200
        assert "This supplier has no services on the Digital Marketplace" in response.get_data(as_text=True)

    def test_should_have_supplier_name_on_services_page(self):
        self.data_api_client.find_services.return_value = {'services': []}

        response = self.client.get('/admin/suppliers/1000/services')

        assert response.status_code == 200
        assert "Supplier Name" in response.get_data(as_text=True)

    def test_should_show_service_details_on_page(self):
        response = self.client.get('/admin/suppliers/1000/services')

        assert response.status_code == 200
        assert "Contract Management" in response.get_data(as_text=True)
        assert '<a href="/g-cloud/services/5687123785023488">' in response.get_data(as_text=True)
        assert "5687123785023488" in response.get_data(as_text=True)
        assert "G-Cloud 8" in response.get_data(as_text=True)
        assert "Software as a Service" in response.get_data(as_text=True)
        assert "Public" in response.get_data(as_text=True)
        assert '<a href="/admin/services/5687123785023488">' in response.get_data(as_text=True)
        assert "Edit" in response.get_data(as_text=True)

    def test_should_show_correct_fields_for_disabled_service(self):
        service = self.load_example_listing("services_response")["services"][0]
        service["status"] = "disabled"
        self.data_api_client.find_services.return_value = {'services': [service]}

        response = self.client.get('/admin/suppliers/1000/services')

        assert response.status_code == 200
        assert "Suspended" in response.get_data(as_text=True)
        assert "Edit" in response.get_data(as_text=True)

    def test_should_show_correct_fields_for_enabled_service(self):
        service = self.load_example_listing("services_response")["services"][0]
        service["status"] = "enabled"
        self.data_api_client.find_services.return_value = {'services': [service]}

        response = self.client.get('/admin/suppliers/1000/services')

        assert response.status_code == 200
        assert "Private" in response.get_data(as_text=True)
        assert "Edit" in response.get_data(as_text=True)

    def test_should_show_correct_fields_for_expired_framework(self):
        framework = self.load_example_listing("framework_response")['frameworks']
        framework['status'] = 'expired'
        self.data_api_client.find_frameworks.return_value = {'frameworks': [framework]}

        response = self.client.get('/admin/suppliers/1000/services')

        assert response.status_code == 200
        assert "Expired" in response.get_data(as_text=True)
        assert "View" in response.get_data(as_text=True)
        assert "Edit" not in response.get_data(as_text=True)

    def test_should_show_separate_tables_for_frameworks_if_supplier_has_service_on_framework(self):

        service_1 = self.load_example_listing("services_response")['services'][0]
        service_2 = service_1.copy()
        service_3 = service_1.copy()
        service_2['frameworkSlug'] = 'digital-outcomes-and-specialists-2'
        service_3['frameworkSlug'] = 'g-cloud-11'
        self.data_api_client.find_services.return_value = {'services': [service_1, service_2, service_3]}

        framework_1 = self.load_example_listing("framework_response")['frameworks']
        framework_2 = framework_1.copy()
        framework_3 = framework_1.copy()
        framework_2['slug'] = 'digital-outcomes-and-specialists-2'
        framework_2['id'] = 5
        framework_3['slug'] = 'g-cloud-11'
        framework_3['id'] = 22
        self.data_api_client.find_frameworks.return_value = {'frameworks': [framework_1, framework_2, framework_3]}

        response = self.client.get('/admin/suppliers/1000/services')

        assert response.status_code == 200

        response_data = response.get_data(as_text=True)
        assert 'g-cloud-11_services' in response_data
        assert 'g-cloud-8_services' in response_data
        assert 'digital-outcomes-and-specialists-2_services' in response_data

        gcloud8_table_index = response_data.find('g-cloud-8_services')
        dos_table_index = response_data.find('digital-outcomes-and-specialists-2_services')
        gcloud11_table_index = response_data.find('g-cloud-11_services')
        assert gcloud11_table_index < gcloud8_table_index < dos_table_index

    def test_remove_all_services_link_if_supplier_has_a_published_service_on_framework(self):
        service_1 = self.load_example_listing("services_response")["services"][0]
        service_2 = service_1.copy()
        service_2["status"] = "disabled"
        service_3 = service_1.copy()
        service_3["status"] = "enabled"

        self.data_api_client.find_services.return_value = {'services': [service_1, service_2, service_3]}

        response = self.client.get('/admin/suppliers/1000/services')
        assert response.status_code == 200

        document = html.fromstring(response.get_data(as_text=True))
        expected_link_text = "Suspend services"
        expected_href = '/admin/suppliers/1234/services?remove=g-cloud-8'
        expected_link = document.xpath('.//a[contains(@href,"{}")]'.format(expected_href))[0]
        assert expected_link.text == expected_link_text

    @pytest.mark.parametrize(
        'framework_status, links_shown',
        [('coming', 0), ('open', 0), ('pending', 0), ('standstill', 0), ('live', 1), ('expired', 0)]
    )
    def test_remove_all_services_link_only_visible_for_live_framework(self, framework_status, links_shown):
        framework = self.load_example_listing("framework_response")['frameworks']
        framework['status'] = framework_status
        self.data_api_client.find_frameworks.return_value = {'frameworks': [framework]}

        response = self.client.get('/admin/suppliers/1000/services')
        assert response.status_code == 200

        document = html.fromstring(response.get_data(as_text=True))
        expected_href = '/admin/suppliers/1234/services?remove=g-cloud-8'
        assert len(document.xpath('.//a[contains(@href,"{}")]'.format(expected_href))) == links_shown

    @pytest.mark.parametrize('service_status, disallowed_actions', [
        ('enabled', ['publish']), ('disabled', ['enabled']), ('a_new_status', ['publish', 'enabled'])
    ])
    def test_toggle_all_services_link_not_shown_for_incorrect_supplier_service_statuses(
        self, service_status, disallowed_actions
    ):
        service = self.load_example_listing('services_response')['services'][0]
        service["status"] = service_status

        self.data_api_client.find_services.return_value = {'services': [service]}

        response = self.client.get('/admin/suppliers/1000/services')
        assert response.status_code == 200

        for action in disallowed_actions:
            document = html.fromstring(response.get_data(as_text=True))
            href = '/admin/suppliers/1234/services?{}=g-cloud-8'.format(action)
            assert len(document.xpath('.//a[contains(@href,"{}")]'.format(href))) == 0


class TestSupplierServicesViewWithToggleSuspendedParam(LoggedInApplicationTest):
    user_role = 'admin-ccs-category'

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.suppliers.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()
        self.data_api_client.get_supplier.return_value = self.load_example_listing('supplier_response')
        self.data_api_client.find_services.return_value = {
            'services': [
                {'id': 1, 'status': 'published', 'frameworkSlug': 'g-cloud-8'},
                {'id': 2, 'status': 'disabled', 'frameworkSlug': 'g-cloud-8'},
            ]
        }
        self.data_api_client.find_frameworks.return_value = {
            'frameworks': [self.load_example_listing("framework_response")['frameworks']]
        }

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    def test_400_if_supplier_has_no_services(self):
        framework = 'digital-outcomes-and-specialists-2'
        self.data_api_client.find_services.return_value = {'services': []}

        response = self.client.get('/admin/suppliers/1000/services?remove={}'.format(framework))

        assert response.status_code == 400

    def test_400_if_supplier_has_no_service_on_framework(self):
        framework = 'digital-outcomes-and-specialists-2'

        response = self.client.get('/admin/suppliers/1000/services?remove={}'.format(framework))

        assert response.status_code == 400

    @pytest.mark.parametrize('service_status', ['enabled', 'disabled', 'a_new_status'])
    def test_400_if_supplier_has_no_published_service_on_framework(self, service_status):
        framework = 'g-cloud-8'
        service = self.load_example_listing('services_response')['services'][0]
        service["status"] = service_status
        self.data_api_client.find_services.return_value = {'services': [service]}

        response = self.client.get('/admin/suppliers/1000/services?remove={}'.format(framework))

        assert response.status_code == 400

    @pytest.mark.parametrize('action', ['remove', 'publish'])
    def test_200_if_supplier_has_published_or_removed_service_on_framework(self, action):
        framework = 'g-cloud-8'

        response = self.client.get('/admin/suppliers/1000/services?{}={}'.format(action, framework))

        assert response.status_code == 200

    @pytest.mark.parametrize('action, message', [('remove', 'suspend'), ('publish', 'unsuspend')])
    def test_are_you_sure_banner_if_supplier_has_service_on_framework(self, action, message):
        framework = 'g-cloud-8'

        response = self.client.get('/admin/suppliers/1000/services?{}={}'.format(action, framework))
        assert response.status_code == 200

        document = html.fromstring(response.get_data(as_text=True))
        expected_banner_message = "Are you sure you want to {} G-Cloud 8 services for ‘Supplier Name’?".format(message)
        banner_message = document.xpath('//p[@class="banner-message"]//text()')[0].strip()
        assert banner_message == expected_banner_message


class TestToggleSupplierServicesView(LoggedInApplicationTest):
    user_role = 'admin-ccs-category'

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.suppliers.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()

        self.data_api_client.get_supplier.return_value = self.load_example_listing('supplier_response')
        self.data_api_client.find_services.return_value = self.load_example_listing('services_response')
        self.data_api_client.get_framework.return_value = self.load_example_listing('framework_response')

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    @pytest.mark.parametrize('url_suffix', ['', '?remove=', '?foo=bar'])
    def test_400_if_no_framework_provided(self, url_suffix):

        response = self.client.post('/admin/suppliers/1000/services{}'.format(url_suffix))

        assert response.status_code == 400

    def test_400_if_supplier_has_no_service_on_framework(self):
        framework = 'g-cloud-8'
        self.data_api_client.find_services.return_value = {'services': []}

        response = self.client.post('/admin/suppliers/1000/services?remove={}'.format(framework))

        assert response.status_code == 400

    @pytest.mark.parametrize('framework_status', ['coming', 'open', 'pending', 'standstill', 'expired'])
    def test_400_if_framework_is_not_live(self, framework_status):
        self.data_api_client.get_framework.return_value = {
            'frameworks': {'status': framework_status}
        }
        response = self.client.post('/admin/suppliers/1000/services?remove=g-cloud-8')

        assert response.status_code == 400

    @pytest.mark.parametrize('action, initial_status, result_status', [
        ('remove', 'published', 'disabled'), ('publish', 'disabled', 'published')
    ])
    def test_toggles_status_for_multiple_services(self, action, initial_status, result_status):
        framework = 'g-cloud-8'
        service_1 = self.load_example_listing('services_response')['services'][0]
        service_2 = service_1.copy()
        service_2['id'] = '5687123785023489'
        service_3 = service_1.copy()
        service_3['id'] = '5687123785023490'
        map(lambda k: k.update({'status': initial_status}), [service_1, service_2, service_3])

        self.data_api_client.find_services.return_value = {
            'services': [service_1, service_2, service_3]
        }

        response = self.client.post('/admin/suppliers/1000/services?{}={}'.format(action, framework))

        assert response.status_code == 302
        assert self.data_api_client.find_services.call_args_list == [
            mock.call(
                supplier_id=1000,
                framework='g-cloud-8',
                status=initial_status  # Enabled services should not be included
            )
        ]
        assert self.data_api_client.update_service_status.call_args_list == [
            mock.call('5687123785023488', result_status, 'test@example.com'),
            mock.call('5687123785023489', result_status, 'test@example.com'),
            mock.call('5687123785023490', result_status, 'test@example.com'),
        ]

    @pytest.mark.parametrize('action, message_action', [
        ('remove', 'suspended'), ('publish', 'unsuspended')
    ])
    def test_flashes_success_message(self, action, message_action):
        framework = 'g-cloud-8'

        response = self.client.post('/admin/suppliers/1000/services?{}={}'.format(action, framework))

        assert response.status_code == 302

        expected_flash_message = "You {} all G-Cloud 8 services for ‘PROACTIS Group Ltd’.".format(message_action)
        with self.client.session_transaction() as session:
            assert session['_flashes'][0][1] == expected_flash_message


class TestSupplierInviteUserView(LoggedInApplicationTest):

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.suppliers.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()

        self.data_api_client.get_supplier.return_value = self.load_example_listing("supplier_response")
        self.data_api_client.find_users_iter.return_value = self.load_example_listing("users_response")['users']

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    @pytest.mark.parametrize("role, expected_code", [
        ("admin", 302),
        ("admin-ccs-category", 302),
        ("admin-ccs-sourcing", 403),
        ("admin-ccs-data-controller", 403),
        ("admin-framework-manager", 403),
        ("admin-manager", 403),
    ])
    @mock.patch('app.main.views.suppliers.send_user_account_email')
    def test_correct_roles_can_invite_user(self, send_user_account_email, role, expected_code):
        self.user_role = role

        response = self.client.post(
            '/admin/suppliers/1234/invite-user',
            data={
                'email_address': 'email@example.com'
            }
        )
        actual_code = response.status_code
        assert actual_code == expected_code, "Unexpected response {} for role {}".format(actual_code, role)

    def test_should_not_accept_bad_email_on_invite_user(self):
        response = self.client.post(
            "/admin/suppliers/1234/invite-user",
            data={'email_address': 'notatallvalid'},
            follow_redirects=True
        )

        assert response.status_code == 400
        assert "Please enter a valid email address" in response.get_data(as_text=True)

    def test_should_not_allow_missing_email_on_invite_user(self):
        response = self.client.post(
            "/admin/suppliers/1234/invite-user",
            data={},
            follow_redirects=True
        )

        assert response.status_code == 400
        assert "Email can not be empty" in response.get_data(as_text=True)

    def test_should_be_a_404_if_non_int_supplier_id(self):
        response = self.client.post(
            "/admin/suppliers/bad/invite-user",
            data={},
            follow_redirects=True
        )

        assert response.status_code == 404
        assert self.data_api_client.call_args_list == []

    def test_should_be_a_404_if_supplier_id_not_found(self):
        self.data_api_client.get_supplier.side_effect = HTTPError(Response(404))

        response = self.client.post(
            "/admin/suppliers/1234/invite-user",
            data={},
            follow_redirects=True
        )

        self.data_api_client.get_supplier.assert_called_once_with(1234)
        assert self.data_api_client.find_users_iter.call_args_list == []
        assert response.status_code == 404

    def test_should_be_a_404_if_supplier_users_not_found(self):
        self.data_api_client.find_users_iter.side_effect = HTTPError(Response(404))

        response = self.client.post(
            "/admin/suppliers/1234/invite-user",
            data={},
            follow_redirects=True
        )

        self.data_api_client.get_supplier.assert_called_once_with(1234)
        self.data_api_client.find_users_iter.assert_called_once_with(1234)
        assert response.status_code == 404

    @mock.patch('app.main.views.suppliers.send_user_account_email')
    def test_should_create_audit_event(self, send_user_account_email):

        res = self.client.post(
            '/admin/suppliers/1234/invite-user',
            data={
                'email_address': 'email@example.com'
            })

        self.data_api_client.create_audit_event.assert_called_once_with(
            audit_type=AuditTypes.invite_user,
            user='test@example.com',
            object_type='suppliers',
            object_id=1234,
            data={'invitedEmail': 'email@example.com'})

        assert res.status_code == 302
        assert res.location == 'http://localhost/admin/suppliers/users?supplier_id=1234'

    @mock.patch('app.main.views.suppliers.send_user_account_email')
    def test_should_not_send_email_if_bad_supplier_id(self, send_user_account_email):
        self.data_api_client.get_supplier.side_effect = HTTPError(Response(404))
        self.data_api_client.find_users_iter.side_effect = HTTPError(Response(404))

        res = self.client.post(
            "/admin/suppliers/1234/invite-user",
            data={
                'email_address': 'this@isvalid.com',
            })

        assert self.data_api_client.find_users_iter.call_args_list == []
        assert send_user_account_email.call_args_list == []
        assert res.status_code == 404

    @mock.patch('app.main.views.suppliers.send_user_account_email')
    def test_should_call_send_email_with_correct_params(self, send_user_account_email):
        with self.app.app_context():
            res = self.client.post(
                "/admin/suppliers/1234/invite-user",
                data={
                    'email_address': 'this@isvalid.com',
                }
            )

            send_user_account_email.assert_called_once_with(
                'supplier',
                'this@isvalid.com',
                current_app.config['NOTIFY_TEMPLATES']['invite_contributor'],
                extra_token_data={
                    'supplier_id': 1234,
                    'supplier_name': 'Supplier Name'
                },
                personalisation={
                    'user': 'The Digital Marketplace team',
                    'supplier': 'Supplier Name'
                }
            )

            assert res.status_code == 302
            assert res.location == 'http://localhost/admin/suppliers/users?supplier_id=1234'

    @mock.patch('app.main.views.suppliers.send_user_account_email')
    def test_should_strip_whitespace_surrounding_invite_user_email_address_field(self, send_user_account_email):
        with self.app.app_context():
            self.client.post(
                "/admin/suppliers/1234/invite-user",
                data={
                    'email_address': '  this@isvalid.com  ',
                }
            )

            send_user_account_email.assert_called_once_with(
                'supplier',
                'this@isvalid.com',
                current_app.config['NOTIFY_TEMPLATES']['invite_contributor'],
                extra_token_data={
                    'supplier_id': 1234,
                    'supplier_name': 'Supplier Name'
                },
                personalisation={
                    'user': 'The Digital Marketplace team',
                    'supplier': 'Supplier Name'
                }
            )

    @mock.patch('dmutils.email.user_account_email.DMNotifyClient')
    def test_should_be_a_503_if_email_fails(self, DMNotifyClient):
        notify_client_mock = mock.Mock()
        notify_client_mock.send_email.side_effect = EmailError("Arrrgh")
        DMNotifyClient.return_value = notify_client_mock

        res = self.client.post(
            "/admin/suppliers/1234/invite-user",
            data={
                'email_address': 'this@isvalid.com',
            })

        assert res.status_code == 503


class TestUpdatingSupplierDetails(LoggedInApplicationTest):

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.suppliers.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()
        self.data_api_client.find_frameworks.return_value = {'frameworks': [
            FrameworkStub(frameworkLiveAtUTC="b", status="live", slug="g-cloud-11").response(),
        ]}
        # TODO: fix test utils bug to reset declaration on init
        supplier_framework = SupplierFrameworkStub(framework_slug="g-cloud-11", declaration={}).response()
        self.data_api_client.get_supplier_frameworks.return_value = {
            "frameworkInterest": [supplier_framework]
        }

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    @pytest.mark.parametrize("allowed_role", ["admin", "admin-ccs-category", "admin-ccs-data-controller"])
    def test_admin_and_ccs_category_roles_can_update_supplier_name(self, allowed_role):
        self.user_role = allowed_role
        self.data_api_client.get_supplier.return_value = {"suppliers": {"id": 1234, "name": "Something Old"}}
        response = self.client.post(
            '/admin/suppliers/1234/edit/name',
            data={'new_supplier_name': 'Something New'}
        )
        assert response.status_code == 302
        assert response.location == 'http://localhost/admin/suppliers/1234'
        self.data_api_client.update_supplier.assert_called_once_with(
            1234, {'name': "Something New"}, "test@example.com"
        )
        self.assert_flashes("The details for ‘Something New’ have been updated.")

    def test_ccs_sourcing_role_can_not_update_supplier_name(self):
        self.user_role = 'admin-ccs-sourcing'
        response = self.client.post(
            '/admin/suppliers/1234/edit/name',
            data={'new_supplier_name': 'Something New'}
        )
        assert response.status_code == 403
        assert self.data_api_client.update_supplier.call_args_list == []

    @pytest.mark.parametrize("role, expected_code", [
        ("admin", 403),
        ("admin-ccs-category", 403),
        ("admin-ccs-sourcing", 403),
        ("admin-ccs-data-controller", 200),
        ("admin-framework-manager", 403),
        ("admin-manager", 403),
    ])
    @pytest.mark.parametrize(
        "detail_type", ['registered-name', 'registered-company-number', 'registered-address', 'duns-number']
    )
    def test_correct_roles_can_edit_supplier_registered_details(self, detail_type, role, expected_code):
        self.user_role = role
        self.data_api_client.get_supplier.return_value = {
            "suppliers": {
                "id": 1234,
                "name": "ABC",
                "registeredCountry": "country:FR",
                "contactInformation": [
                    {
                        'id': 999,
                        'address1': '123 Rue Morgue',
                        'city': 'Paris',
                        'postcode': '76876',
                        'country': "country:FR"
                    }
                ]
            }
        }
        response = self.client.get('/admin/suppliers/1000/edit/{}'.format(detail_type))
        actual_code = response.status_code
        assert actual_code == expected_code, "Unexpected response {} for role {}".format(actual_code, role)

    @pytest.mark.parametrize('from_declaration', [True, False])
    def test_data_controller_role_can_update_registered_company_name(self, from_declaration):
        self.user_role = 'admin-ccs-data-controller'
        if from_declaration:
            self.data_api_client.get_supplier_frameworks.return_value = {
                'frameworkInterest': [
                    SupplierFrameworkStub(framework_slug="g-cloud-11", with_declaration=True).response()
                ]
            }
        self.data_api_client.get_supplier.return_value = {
            "suppliers": {
                "id": 1000,
                "registeredName": "Something Old",
                "name": "ABC",
                "contactInformation": []
            }
        }
        response = self.client.post(
            '/admin/suppliers/1000/edit/registered-name',
            data={'registered_company_name': "Something New"}
        )
        assert response.status_code == 302
        assert response.location == 'http://localhost/admin/suppliers/1000'
        self.data_api_client.update_supplier.assert_called_once_with(
            1000, {'registeredName': "Something New"}, "test@example.com"
        )
        assert self.data_api_client.update_supplier_declaration.call_args_list == ([
            mock.call(
                1000, 'g-cloud-11',
                {'supplierRegisteredName': "Something New"}, "test@example.com"
            )
        ] if from_declaration else [])
        self.assert_flashes("The details for ‘ABC’ have been updated.")

    @pytest.mark.parametrize('update_declaration', [True, False])
    def test_data_controller_role_can_update_companies_house_number(self, update_declaration):
        self.user_role = 'admin-ccs-data-controller'
        self.data_api_client.get_supplier.return_value = {
            "suppliers": {
                "id": 1234,
                "companiesHouseNumber": "87654321",
                "name": "ABC",
                "contactInformation": []
            }
        }
        if update_declaration:
            self.data_api_client.get_supplier_frameworks.return_value = {
                'frameworkInterest': [
                    SupplierFrameworkStub(framework_slug="g-cloud-11", with_declaration=True).response()
                ]
            }
        response = self.client.post(
            '/admin/suppliers/1234/edit/registered-company-number',
            data={'companies_house_number': '12345678'}
        )
        assert response.status_code == 302
        assert response.location == 'http://localhost/admin/suppliers/1234'
        self.data_api_client.update_supplier.assert_called_once_with(
            1234,
            {
                'companiesHouseNumber': "12345678",
                'otherCompanyRegistrationNumber': None,
            },
            "test@example.com"
        )
        assert self.data_api_client.update_supplier_declaration.call_args_list == ([
            mock.call(
                1234, 'g-cloud-11',
                {'supplierCompanyRegistrationNumber': "12345678"}, "test@example.com"
            )
        ] if update_declaration else [])
        self.assert_flashes("The details for ‘ABC’ have been updated.")

    @pytest.mark.parametrize('update_declaration', [True, False])
    def test_data_controller_role_can_update_other_registration_number(self, update_declaration):
        self.user_role = 'admin-ccs-data-controller'
        self.data_api_client.get_supplier.return_value = {
            "suppliers": {
                "id": 1234,
                "otherCompanyRegistrationNumber": "abc123456",
                "name": "ABC",
                "contactInformation": []
            }
        }
        if update_declaration:
            self.data_api_client.get_supplier_frameworks.return_value = {
                'frameworkInterest': [
                    SupplierFrameworkStub(framework_slug="g-cloud-11", with_declaration=True).response()
                ]
            }
        response = self.client.post(
            '/admin/suppliers/1234/edit/registered-company-number',
            data={'other_company_registration_number': 'def98765'}
        )
        assert response.status_code == 302
        assert response.location == 'http://localhost/admin/suppliers/1234'
        self.data_api_client.update_supplier.assert_called_once_with(
            1234,
            {
                'companiesHouseNumber': None,
                'otherCompanyRegistrationNumber': "def98765",
            },
            "test@example.com"
        )
        assert self.data_api_client.update_supplier_declaration.call_args_list == ([
            mock.call(
                1234, 'g-cloud-11',
                {'supplierCompanyRegistrationNumber': "def98765"}, "test@example.com"
            )
        ] if update_declaration else [])
        self.assert_flashes("The details for ‘ABC’ have been updated.")

    @pytest.mark.parametrize('update_declaration', [True, False])
    def test_data_controller_role_can_change_companies_house_to_other_registration_number(self, update_declaration):
        self.user_role = 'admin-ccs-data-controller'
        self.data_api_client.get_supplier.return_value = {
            "suppliers": {
                "id": 1234,
                "companiesHouseNumber": "12345678",
                "name": "ABC",
                "contactInformation": []
            }
        }
        if update_declaration:
            self.data_api_client.get_supplier_frameworks.return_value = {
                'frameworkInterest': [
                    SupplierFrameworkStub(framework_slug="g-cloud-11", with_declaration=True).response()
                ]
            }
        response = self.client.post(
            '/admin/suppliers/1234/edit/registered-company-number',
            data={
                'companies_house_number': '',
                'other_company_registration_number': 'def98765'
            }
        )
        assert response.status_code == 302
        assert response.location == 'http://localhost/admin/suppliers/1234'
        self.data_api_client.update_supplier.assert_called_once_with(
            1234,
            {
                'companiesHouseNumber': None,
                'otherCompanyRegistrationNumber': "def98765",
            },
            "test@example.com"
        )
        assert self.data_api_client.update_supplier_declaration.call_args_list == ([
            mock.call(
                1234, 'g-cloud-11',
                {'supplierCompanyRegistrationNumber': "def98765"}, "test@example.com"
            )
        ] if update_declaration else [])
        self.assert_flashes("The details for ‘ABC’ have been updated.")

    @pytest.mark.parametrize('from_declaration', [True, False])
    def test_data_controller_role_can_update_registered_company_address(self, from_declaration):
        self.user_role = 'admin-ccs-data-controller'
        if from_declaration:
            self.data_api_client.get_supplier_frameworks.return_value = {
                'frameworkInterest': [
                    SupplierFrameworkStub(framework_slug="g-cloud-11", with_declaration=True).response()
                ]
            }
        self.data_api_client.get_supplier.return_value = {
            "suppliers": {
                "id": 1234,
                "name": "ABC",
                "registeredCountry": "country:FR",
                "contactInformation": [
                    {
                        'id': 999,
                        'address1': '123 Rue Morgue',
                        'city': 'Paris',
                        'postcode': '76876',
                        'country': "country:FR"
                    }
                ]
            }
        }
        response = self.client.post(
            '/admin/suppliers/1234/edit/registered-address',
            data={
                'street': '10 Downing St',
                'city': 'London',
                'postcode': 'AB1 2DE',
                'country': 'country:GB'
            }
        )
        assert response.status_code == 302
        assert response.location == 'http://localhost/admin/suppliers/1234'
        self.data_api_client.update_supplier.assert_called_once_with(
            1234, {'registrationCountry': "country:GB"}, "test@example.com"
        )
        self.data_api_client.update_contact_information.assert_called_once_with(
            1234,
            999,
            {
                'address1': '10 Downing St',
                'city': 'London',
                'postcode': 'AB1 2DE',
                'country': "country:GB"
            },
            "test@example.com"
        )
        assert self.data_api_client.update_supplier_declaration.call_args_list == ([
            mock.call(
                1234, 'g-cloud-11',
                {
                    "supplierRegisteredBuilding": '10 Downing St',
                    "supplierRegisteredCountry": "country:GB",
                    "supplierRegisteredPostcode": 'AB1 2DE',
                    "supplierRegisteredTown": 'London',
                }, "test@example.com"
            )
        ] if from_declaration else [])
        self.assert_flashes("The details for ‘ABC’ have been updated.")

    @pytest.mark.parametrize(
        'url_suffix, payload, expected_error_msg', [
            ('registered-company-number', {'companies_house_number': ''}, "You must provide an answer"),
            ('registered-name', {'registered_company_name': ''}, "You must provide a registered company name"),
        ]
    )
    def test_edit_company_name_or_number_shows_validation_header_on_400(self, url_suffix, payload, expected_error_msg):
        self.user_role = 'admin-ccs-data-controller'
        self.data_api_client.get_supplier.return_value = {
            "suppliers": {
                "id": 1234,
                "companiesHouseNumber": "87654321",
                "name": "ABC",
                "contactInformation": []
            }
        }
        response = self.client.post(
            '/admin/suppliers/1234/edit/{}'.format(url_suffix),
            data=payload
        )
        assert response.status_code == 400
        assert self.data_api_client.update_supplier.called is False
        assert self.data_api_client.update_supplier_declaration.called is False
        assert expected_error_msg in response.get_data(as_text=True)
        document = html.fromstring(response.get_data(as_text=True))
        validation_banner_h2 = document.xpath("//h2[@class='validation-masthead-heading']//text()")[0].strip()
        assert validation_banner_h2 == "There was a problem with your answer to:"

    def test_edit_duns_number_shows_contact_us_message(self):
        self.user_role = 'admin-ccs-data-controller'
        response = self.client.get('/admin/suppliers/1000/edit/duns-number')
        assert response.status_code == 200
        assert "You need to contact" in response.get_data(as_text=True)


class TestViewingASupplierDeclaration(LoggedInApplicationTest):
    user_role = 'admin-ccs-sourcing'

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.suppliers.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()

        self.data_api_client.get_supplier.return_value = self.load_example_listing('supplier_response')
        self.data_api_client.get_framework.return_value = self.load_example_listing('framework_response')
        self.data_api_client.get_supplier_declaration.return_value = self.load_example_listing('declaration_response')

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    def test_should_not_be_visible_to_admin_users(self):
        self.user_role = 'admin'

        response = self.client.get('/admin/suppliers/1234/edit/declarations/g-cloud-7')

        assert response.status_code == 403

    def test_should_404_if_supplier_does_not_exist(self):
        self.data_api_client.get_supplier.side_effect = APIError(Response(404))

        response = self.client.get('/admin/suppliers/1234/edit/declarations/g-cloud-7')

        assert response.status_code == 404
        self.data_api_client.get_supplier.assert_called_once_with(1234)
        assert self.data_api_client.get_framework.call_args_list == []

    def test_should_404_if_framework_does_not_exist(self):
        self.data_api_client.get_framework.side_effect = APIError(Response(404))

        response = self.client.get('/admin/suppliers/1234/edit/declarations/g-cloud-7')

        assert response.status_code == 404
        self.data_api_client.get_supplier.assert_called_with(1234)
        self.data_api_client.get_framework.assert_called_with('g-cloud-7')

    def test_should_not_404_if_declaration_does_not_exist(self):
        self.data_api_client.get_supplier_declaration.side_effect = APIError(Response(404))

        response = self.client.get('/admin/suppliers/1234/edit/declarations/g-cloud-7')

        assert response.status_code == 200
        self.data_api_client.get_supplier.assert_called_once_with(1234)
        self.data_api_client.get_framework.assert_called_once_with('g-cloud-7')
        self.data_api_client.get_supplier_declaration.assert_called_once_with(1234, 'g-cloud-7')

    def test_should_show_declaration(self):
        response = self.client.get('/admin/suppliers/1234/edit/declarations/g-cloud-7')
        document = html.fromstring(response.get_data(as_text=True))

        assert response.status_code == 200
        data = document.cssselect('.summary-item-row td.summary-item-field')
        assert data[0].text_content().strip() == "Yes"

    def test_should_show_dos_declaration(self):
        response = self.client.get('/admin/suppliers/1234/edit/declarations/digital-outcomes-and-specialists')
        document = html.fromstring(response.get_data(as_text=True))

        assert response.status_code == 200
        data = document.cssselect('.summary-item-row td.summary-item-field')
        assert data[0].text_content().strip() == "Yes"

    def test_should_403_if_framework_is_open(self):
        self.data_api_client.get_framework.return_value['frameworks']['status'] = 'open'

        response = self.client.get('/admin/suppliers/1234/edit/declarations/digital-outcomes-and-specialists')
        assert response.status_code == 403


class TestEditingASupplierDeclaration(LoggedInApplicationTest):
    user_role = 'admin-ccs-sourcing'

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.suppliers.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()
        self.data_api_client.get_supplier.return_value = self.load_example_listing('supplier_response')
        self.data_api_client.get_framework.return_value = self.load_example_listing('framework_response')
        self.data_api_client.get_supplier_declaration.return_value = self.load_example_listing('declaration_response')

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    def test_should_not_be_visible_to_admin_users(self):
        self.user_role = 'admin'

        response = self.client.get('/admin/suppliers/1234/edit/declarations/g-cloud-7/section')

        assert response.status_code == 403

    def test_should_404_if_supplier_does_not_exist(self):
        self.data_api_client.get_supplier.side_effect = APIError(Response(404))

        response = self.client.get('/admin/suppliers/1234/edit/declarations/g-cloud-7/g-cloud-7-essentials')

        assert response.status_code == 404
        self.data_api_client.get_supplier.assert_called_once_with(1234)
        assert self.data_api_client.get_framework.call_args_list == []

    def test_should_404_if_framework_does_not_exist(self):
        self.data_api_client.get_framework.side_effect = APIError(Response(404))

        response = self.client.get('/admin/suppliers/1234/edit/declarations/g-cloud-7/g-cloud-7-essentials')

        assert response.status_code == 404
        self.data_api_client.get_supplier.assert_called_once_with(1234)
        self.data_api_client.get_framework.assert_called_once_with('g-cloud-7')

    def test_should_404_if_section_does_not_exist(self):
        self.data_api_client.get_supplier_declaration.side_effect = APIError(Response(404))

        response = self.client.get('/admin/suppliers/1234/edit/declarations/g-cloud-7/not_a_section')

        assert response.status_code == 404

    def test_should_not_404_if_declaration_does_not_exist(self):
        self.data_api_client.get_supplier_declaration.side_effect = APIError(Response(404))

        response = self.client.get('/admin/suppliers/1234/edit/declarations/g-cloud-7/g-cloud-7-essentials')

        assert response.status_code == 200
        self.data_api_client.get_supplier.assert_called_once_with(1234)
        self.data_api_client.get_framework.assert_called_once_with('g-cloud-7')
        self.data_api_client.get_supplier_declaration.assert_called_once_with(1234, 'g-cloud-7')

    def test_should_prefill_form_with_declaration(self):
        response = self.client.get('/admin/suppliers/1234/edit/declarations/g-cloud-7/g-cloud-7-essentials')
        document = html.fromstring(response.get_data(as_text=True))

        assert response.status_code == 200
        assert document.cssselect('#input-PR1-1')[0].checked
        assert not document.cssselect('#input-PR1-2')[0].checked

    def test_should_set_declaration(self):
        self.client.post(
            '/admin/suppliers/1234/edit/declarations/g-cloud-7/g-cloud-7-essentials',
            data={'PR1': 'false'})

        declaration = self.load_example_listing('declaration_response')['declaration']
        declaration['PR1'] = False
        declaration['SQ1-3'] = None
        declaration['SQC3'] = None

        self.data_api_client.set_supplier_declaration.assert_called_once_with(
            1234, 'g-cloud-7', declaration, 'test@example.com')


@mock.patch('app.main.views.suppliers.download_agreement_file')
class TestDownloadSignedAgreementFile(LoggedInApplicationTest):
    user_role = 'admin-ccs-sourcing'

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.suppliers.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    def test_download_agreement_is_called_with_the_right_parameters(self, download_agreement_file):
        self.data_api_client.get_supplier_framework_info.return_value = {
            'frameworkInterest': {'agreementPath': '/path/to/file/in/s3/1234-signed-agreement-file.pdf'}
        }
        # Mock out a response from download_agreement_file() - we don't care what it is
        download_agreement_file.side_effect = HTTPError(Response(404))
        self.client.get('/admin/suppliers/1234/agreement/g-cloud-7')
        download_agreement_file.assert_called_once_with(1234, 'g-cloud-7', 'signed-agreement-file.pdf')

    def test_should_404_if_supplier_agreement_has_no_agreement_path(self, download_agreement_file):
        self.data_api_client.get_supplier_framework_info.return_value = {
            'frameworkInterest': {'agreementPath': None}
        }
        response = self.client.get('/admin/suppliers/1234/agreement/g-cloud-8')

        assert response.status_code == 404
        self.data_api_client.get_supplier_framework_info.assert_called_once_with(1234, 'g-cloud-8')
        assert download_agreement_file.called is False


@mock.patch('app.main.views.suppliers.s3')
class TestDownloadAgreementFile(LoggedInApplicationTest):
    user_role = 'admin-ccs-sourcing'

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.suppliers.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()

        self.data_api_client.get_supplier_framework_info.return_value = {
            'frameworkInterest': {'declaration': {'key': 'Supplier name'}}
        }

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    @pytest.mark.parametrize("role, expected_code", [
        ("admin", 403),
        ("admin-ccs-category", 302),
        ("admin-ccs-sourcing", 302),
        ("admin-ccs-data-controller", 302),
        ("admin-framework-manager", 302),
        ("admin-manager", 403),
    ])
    def test_download_agreement_file_accessible_to_specific_user_roles(self, s3, role, expected_code):
        self.user_role = role
        s3.S3.return_value.get_signed_url.return_value = 'http://foo/blah?extra'

        response = self.client.get('/admin/suppliers/1234/agreements/g-cloud-7/foo.pdf')
        actual_code = response.status_code
        assert actual_code == expected_code, "Unexpected response {} for role {}".format(actual_code, role)

    def test_should_404_if_no_supplier_framework_declaration(self, s3):
        self.data_api_client.get_supplier_framework_info.return_value = {
            'frameworkInterest': {'declaration': None}
        }
        response = self.client.get('/admin/suppliers/1234/agreements/g-cloud-7/foo.pdf')
        assert response.status_code == 404

    def test_should_404_if_document_does_not_exist(self, s3):
        self.data_api_client.get_supplier_framework_info.return_value = {
            'frameworkInterest': {'declaration': {'SQ1-1a': 'Supplier name'}}
        }
        s3.S3.return_value.get_signed_url.return_value = None

        response = self.client.get('/admin/suppliers/1234/agreements/g-cloud-7/foo.pdf')

        s3.S3.return_value.get_signed_url.assert_called_once_with('g-cloud-7/agreements/1234/1234-foo.pdf')
        assert response.status_code == 404

    def test_should_redirect(self, s3):
        s3.S3.return_value.get_signed_url.return_value = 'http://foo/blah?extra'

        self.app.config['DM_ASSETS_URL'] = 'https://example'

        response = self.client.get('/admin/suppliers/1234/agreements/g-cloud-7/foo.pdf')

        s3.S3.return_value.get_signed_url.assert_called_once_with('g-cloud-7/agreements/1234/1234-foo.pdf')
        assert response.status_code == 302
        assert response.location == 'https://example/blah?extra'

    def test_admin_should_be_able_to_download_countersigned_agreement(self, s3):
        s3.S3.return_value.get_signed_url.return_value = 'http://foo/blah?extra'
        self.app.config['DM_ASSETS_URL'] = 'https://example'

        response = self.client.get(
            '/admin/suppliers/1234/agreements/g-cloud-7/countersigned-framework-agreement.pdf'
        )

        s3.S3.return_value.get_signed_url.assert_called_once_with(
            'g-cloud-7/agreements/1234/1234-countersigned-framework-agreement.pdf'
        )
        assert response.status_code == 302


@mock.patch('app.main.views.suppliers.s3')
class TestListCountersignedAgreementFile(LoggedInApplicationTest):
    user_role = 'admin-ccs-sourcing'

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.suppliers.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    def test_should_not_be_visible_to_admin_users(self, s3):
        self.user_role = 'admin'

        response = self.client.get('/admin/suppliers/1234/countersigned-agreements/g-cloud-7')

        assert response.status_code == 403

    def test_should_be_visible_to_admin_sourcing_users(self, s3):
        s3.S3.return_value.get_key.return_value = {
            'size': '7050',
            'path': u'g-cloud-7/agreements/93495/93495-countersigned-framework-agreement.pdf',
            'ext': u'pdf',
            'last_modified': u'2016-01-15T12:58:08.000000Z',
            'filename': u'93495-countersigned-framework-agreement'
        }
        self.data_api_client.get_supplier_framework_info.return_value = \
            {"frameworkInterest": {
                "onFramework": True,
                "agreementStatus": "signed",
                "countersignedPath": "g-cloud-7/agreements/93495/93495-countersigned-framework-agreement.pdf"
            }}

        response = self.client.get('/admin/suppliers/1234/countersigned-agreements/g-cloud-7')
        assert response.status_code == 200

    def test_should_display_no_documents_if_no_documents_listed(self, s3):
        s3.S3.return_value.get_key.return_value = []
        self.data_api_client.get_supplier_framework_info.return_value = {
            "frameworkInterest": {
                "onFramework": True,
                "agreementStatus": "signed",
                "countersignedPath": None
            }
        }

        response = self.client.get('/admin/suppliers/1234/countersigned-agreements/g-cloud-7')
        assert 'No agreements have been uploaded' in response.get_data(as_text=True)

    @pytest.mark.parametrize(
        'confirmation_param_value,confirmation_message_shown',
        [('true', True), ('false', False), (0, False), ('', False)]
    )
    def test_remove_countersigned_agreement_confirmation_flag(
            self, s3, confirmation_param_value, confirmation_message_shown
    ):
        s3.S3.return_value.get_key.return_value = {
            'size': '7050',
            'path': u'g-cloud-7/agreements/93495/93495-countersigned-framework-agreement.pdf',
            'ext': u'pdf',
            'last_modified': u'2016-01-15T12:58:08.000000Z',
            'filename': u'93495-countersigned-framework-agreement'
        }
        self.data_api_client.get_supplier_framework_info.return_value = \
            {"frameworkInterest": {
                "onFramework": True,
                "agreementStatus": "signed",
                "countersignedPath": "g-cloud-7/agreements/93495/93495-countersigned-framework-agreement.pdf"
            }}

        response = self.client.get(
            '/admin/suppliers/1234/countersigned-agreements/g-cloud-7?remove_countersigned_agreement={}'.format(
                confirmation_param_value
            )
        )

        assert ('Do you want to remove the countersigned agreement?' in response.get_data(as_text=True)) == \
            confirmation_message_shown


@freeze_time('2016-12-25 06:30:01')
@mock.patch('app.main.views.suppliers.s3')
class TestUploadCountersignedAgreementFile(LoggedInApplicationTest):
    user_role = 'admin-ccs-sourcing'

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.suppliers.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    def test_countersigned_agreement_displays_error_for_wrong_format(self, s3):
        s3.S3.return_value.get_key.return_value = {
            'size': '7050',
            'path': u'g-cloud-7/agreements/93495/93495-countersigned-framework-agreement.pdf',
            'ext': u'pdf',
            'last_modified': u'2016-01-15T12:58:08.000000Z',
            'filename': u'93495-countersigned-framework-agreement'
        }
        self.data_api_client.get_supplier_framework_info.return_value = \
            {"frameworkInterest": {
                "onFramework": True,
                "agreementStatus": "signed",
                "agreementId": 1212,
                "countersignedPath": "g-cloud-7/agreements/93495/93495-countersigned-framework-agreement.pdf"
            }}

        response = self.client.post('/admin/suppliers/1234/countersigned-agreements/g-cloud-7',
                                    data=dict(
                                        countersigned_agreement=(BytesIO(b"this is a test"),
                                                                 'test.odt'), ), follow_redirects=True)

        assert 'This must be a pdf' in response.get_data(as_text=True)
        assert response.status_code == 200

    def test_can_upload_countersigned_agreement_for_signed_agreement(self, s3):
        expected_countersign_path = 'g-cloud-7/agreements/1234/1234-agreement-countersignature-2016-12-25-063001.pdf'
        s3.S3.return_value.get_key.return_value = {
            'size': '7050',
            'path': u'g-cloud-7/agreements/1234/1234-countersigned-framework-agreement.pdf',
            'ext': u'pdf',
            'last_modified': u'2016-01-15T12:58:08.000000Z',
            'filename': u'1234-countersigned-framework-agreement'
        }
        self.data_api_client.get_supplier_framework_info.return_value = {
            "frameworkInterest": {
                "onFramework": True,
                "agreementStatus": "signed",
                "agreementId": 1212,
                "countersignedPath": None,
                "declaration": {"nameOfOrganisation": "Supplier Mc Supply Face"},
            }
        }
        response = self.client.post(
            '/admin/suppliers/1234/countersigned-agreements/g-cloud-7',
            data={'countersigned_agreement': (BytesIO(valid_pdf_bytes), 'countersigned_agreement.pdf')}
        )

        self.data_api_client.approve_agreement_for_countersignature.assert_called_once_with(
            1212,
            'test@example.com',
            '1234'
        )

        s3.S3.return_value.save.assert_called_once_with(
            expected_countersign_path,
            mock.ANY,
            acl='bucket-owner-full-control',
            move_prefix=None,
            download_filename='Supplier_Mc_Supply_Face-1234-agreement-countersignature.pdf'
        )

        self.data_api_client.update_framework_agreement.assert_called_once_with(
            1212,
            {"countersignedAgreementPath": expected_countersign_path},
            'test@example.com'
        )

        self.data_api_client.create_audit_event.assert_called_once_with(
            audit_type=AuditTypes.upload_countersigned_agreement,
            user='test@example.com',
            object_type='suppliers',
            object_id=1234,
            data={'upload_countersigned_agreement': expected_countersign_path}
        )

        assert response.status_code == 302
        assert response.location == 'http://localhost/admin/suppliers/1234/countersigned-agreements/g-cloud-7'

    def test_can_upload_countersigned_agreement_for_already_countersigned_agreement(self, s3):
        s3.S3.return_value.get_key.return_value = {
            'size': '7050',
            'path': u'g-cloud-7/agreements/1234/1234-countersigned-framework-agreement.pdf',
            'ext': u'pdf',
            'last_modified': u'2016-01-15T12:58:08.000000Z',
            'filename': u'1234-countersigned-framework-agreement'
        }
        self.data_api_client.get_supplier_framework_info.return_value = \
            {"frameworkInterest": {
                "onFramework": True,
                "agreementStatus": "countersigned",
                "agreementId": 1212,
                "countersignedPath": "g-cloud-7/agreements/1234/1234-agreement-countersignature-2016-12-25-063001.pdf",  # noqa
                "declaration": {"nameOfOrganisation": "Supplier Mc Supply Face"},
            }}
        response = self.client.post('/admin/suppliers/1234/countersigned-agreements/g-cloud-7',
                                    data=dict(
                                        countersigned_agreement=(BytesIO(valid_pdf_bytes),
                                                                 'countersigned_agreement.pdf'),
                                    ))

        assert self.data_api_client.approve_agreement_for_countersignature.call_args_list == []

        s3.S3.return_value.save.assert_called_once_with(
            "g-cloud-7/agreements/1234/1234-agreement-countersignature-2016-12-25-063001.pdf",
            mock.ANY,
            acl='bucket-owner-full-control',
            move_prefix=None,
            download_filename='Supplier_Mc_Supply_Face-1234-agreement-countersignature.pdf'
        )

        self.data_api_client.update_framework_agreement.assert_called_once_with(
            1212,
            {"countersignedAgreementPath": "g-cloud-7/agreements/1234/1234-agreement-countersignature-2016-12-25-063001.pdf"},  # noqa
            'test@example.com'
        )

        self.data_api_client.create_audit_event.assert_called_once_with(
            audit_type=AuditTypes.upload_countersigned_agreement,
            user='test@example.com',
            object_type='suppliers',
            object_id=1234,
            data={
                'upload_countersigned_agreement':
                    'g-cloud-7/agreements/1234/1234-agreement-countersignature-2016-12-25-063001.pdf'}
        )

        assert response.status_code == 302
        assert response.location == 'http://localhost/admin/suppliers/1234/countersigned-agreements/g-cloud-7'

    def test_can_upload_countersigned_agreement_for_framework_without_declaration(self, s3):
        s3.S3.return_value.get_key.return_value = {
            'size': '7050',
            'path': u'g-cloud-7/agreements/1234/1234-countersigned-framework-agreement.pdf',
            'ext': u'pdf',
            'last_modified': u'2016-01-15T12:58:08.000000Z',
            'filename': u'1234-countersigned-framework-agreement'
        }
        self.data_api_client.get_supplier_framework_info.return_value = \
            {"frameworkInterest": {
                "onFramework": True,
                "agreementStatus": "signed",
                "agreementId": 1212,
                "countersignedPath": None
            }}
        self.data_api_client.get_supplier.return_value = \
            {"suppliers": {
                "name": "DM Supplier Name"
            }}
        response = self.client.post('/admin/suppliers/1234/countersigned-agreements/g-cloud-7',
                                    data=dict(
                                        countersigned_agreement=(BytesIO(valid_pdf_bytes),
                                                                 'countersigned_agreement.pdf'),
                                    ))

        self.data_api_client.approve_agreement_for_countersignature.assert_called_once_with(
            1212,
            'test@example.com',
            '1234'
        )

        s3.S3.return_value.save.assert_called_once_with(
            "g-cloud-7/agreements/1234/1234-agreement-countersignature-2016-12-25-063001.pdf",
            mock.ANY,
            acl='bucket-owner-full-control',
            move_prefix=None,
            download_filename='DM_Supplier_Name-1234-agreement-countersignature.pdf'
        )

        self.data_api_client.update_framework_agreement.assert_called_once_with(
            1212,
            {
                "countersignedAgreementPath": "g-cloud-7/agreements/1234/1234-agreement-countersignature-2016-12-25-063001.pdf"},  # noqa
            'test@example.com'
        )

        assert response.status_code == 302
        assert response.location == 'http://localhost/admin/suppliers/1234/countersigned-agreements/g-cloud-7'
        self.data_api_client.create_audit_event.assert_called_once_with(
            audit_type=AuditTypes.upload_countersigned_agreement,
            user='test@example.com',
            object_type='suppliers',
            object_id=1234,
            data={
                'upload_countersigned_agreement':
                    'g-cloud-7/agreements/1234/1234-agreement-countersignature-2016-12-25-063001.pdf'
            }
        )


@mock.patch('app.main.views.suppliers.s3')
class TestRemoveCountersignedAgreementFile(LoggedInApplicationTest):
    user_role = 'admin-ccs-sourcing'

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.suppliers.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    def test_should_remove_countersigned_agreement(self, s3):
        s3.S3.return_value.delete_key.return_value = {'Key': 'digitalmarketplace-documents-dev-dev'
                                                      ',g-cloud-7/agreements/93495/93495-'
                                                      'countersigned-framework-agreement.pdf'}
        response = self.client.post('/admin/suppliers/1234/countersigned-agreements-remove/g-cloud-7')
        assert response.status_code == 302

    def test_admin_should_not_be_able_to_remove_countersigned_agreement(self, s3):
        self.user_role = 'admin'
        s3.S3.return_value.delete_key.return_value = {'Key': 'digitalmarketplace-documents-dev-dev'
                                                      ',g-cloud-7/agreements/93495/93495-'
                                                      'countersigned-framework-agreement.pdf'}
        response = self.client.post('/admin/suppliers/1234/countersigned-agreements-remove/g-cloud-7')
        assert response.status_code == 403

    def test_should_display_remove_countersigned_agreement_message(self, s3):
        s3.S3.return_value.get_key.return_value = {
            'size': '7050',
            'path': u'g-cloud-7/agreements/93495/93495-countersigned-framework-agreement.pdf',
            'ext': u'pdf',
            'last_modified': u'2016-01-15T12:58:08.000000Z',
            'filename': u'93495-countersigned-framework-agreement'
        }
        self.data_api_client.get_supplier_framework_info.return_value = \
            {"frameworkInterest": {
                "onFramework": True,
                "agreementStatus": "signed",
                "countersignedPath": "g-cloud-7/agreements/93495/93495-countersigned-framework-agreement.pdf"
            }}
        response = self.client.get('/admin/suppliers/1234/countersigned-agreements-remove/g-cloud-7',
                                   follow_redirects=True)
        assert 'Do you want to remove the countersigned agreement?' in response.get_data(as_text=True)
        assert response.status_code == 200


@mock.patch('app.main.views.suppliers.s3')
class TestViewingSignedAgreement(LoggedInApplicationTest):
    user_role = 'admin-ccs-sourcing'

    services_response = (
        {
            "id": 1111,
            "lotSlug": "dried-fruit",
            "lotName": "Raisins & dates",
        },
        {
            "id": 2222,
            "lotSlug": "salad",
            "lotName": "Lettuce & cucumber",
        },
        {
            "id": 3333,
            "lotSlug": "dried-fruit",
            "lotName": "Raisins & dates",
        },
    )

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.suppliers.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()
        self.data_api_client.get_supplier.return_value = self.load_example_listing('supplier_response')
        self.data_api_client.get_framework.return_value = self.load_example_listing('framework_response')
        self.data_api_client.get_supplier_framework_info.return_value = self.load_example_listing(
            'supplier_framework_response'
        )

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    def test_should_404_if_supplier_does_not_exist(self, s3):
        self.data_api_client.get_supplier.side_effect = APIError(Response(404))

        response = self.client.get('/admin/suppliers/1234/agreements/g-cloud-8')

        assert response.status_code == 404
        self.data_api_client.get_supplier.assert_called_with(1234)
        assert self.data_api_client.get_framework.call_args_list == []

    def test_should_404_if_framework_does_not_exist(self, s3):
        self.data_api_client.get_framework.side_effect = APIError(Response(404))

        response = self.client.get('/admin/suppliers/1234/agreements/g-cloud-8')

        assert response.status_code == 404
        self.data_api_client.get_supplier.assert_called_once_with(1234)
        self.data_api_client.get_framework.assert_called_once_with('g-cloud-8')

    def test_should_404_if_agreement_not_returned(self, s3):
        not_returned = self.load_example_listing('supplier_framework_response')
        not_returned['frameworkInterest']['agreementReturned'] = False
        self.data_api_client.get_supplier_framework_info.return_value = not_returned
        response = self.client.get('/admin/suppliers/1234/agreements/g-cloud-8')

        assert response.status_code == 404
        self.data_api_client.get_supplier.assert_called_once_with(1234)
        self.data_api_client.get_framework.assert_called_once_with('g-cloud-8')
        self.data_api_client.get_supplier_framework_info.assert_called_once_with(1234, 'g-cloud-8')

    def test_should_404_if_agreement_has_no_version(self, s3):
        self.data_api_client.get_framework.return_value = {'frameworks': {}}
        response = self.client.get('/admin/suppliers/1234/agreements/g-cloud-8')

        assert response.status_code == 404
        self.data_api_client.get_supplier.assert_called_once_with(1234)
        self.data_api_client.get_framework.assert_called_once_with('g-cloud-8')

    def test_should_show_agreement_details_on_page(self, s3):
        self.data_api_client.find_services_iter.return_value = iter(self.services_response)

        with mock.patch('app.main.views.suppliers.get_signed_url') as mock_get_url:
            mock_get_url.return_value = "http://example.com/document/1234.pdf"

            response = self.client.get('/admin/suppliers/1234/agreements/g-cloud-8')
            document = html.fromstring(response.get_data(as_text=True))
            assert response.status_code == 200
            # Registered Address
            assert len(document.xpath('//li[contains(text(), "Corsewall Lighthouse")]')) == 1
            assert len(document.xpath('//li[contains(text(), "Stranraer")]')) == 1
            assert len(document.xpath('//li[contains(text(), "DG9 0QG")]')) == 1
            # Company number - linked
            assert len(document.xpath('//a[@href="https://beta.companieshouse.gov.uk/company/1234456"][contains(text(), "1234456")]')) == 1  # noqa
            # Lots
            assert len(document.xpath('//li[contains(text(), "Lettuce & cucumber")]')) == 1
            assert len(document.xpath('//li[contains(text(), "Raisins & dates")]')) == 1
            # Signer details
            assert len(document.xpath('//p[contains(text(), "Signer Name")]')) == 1
            assert len(document.xpath('//p[contains(text(), "Ace Developer")]')) == 1
            # Uploader details
            assert len(document.xpath('//p[contains(text(), "Uploader Name")]')) == 1
            assert len(document.xpath('//span[contains(text(), "uploader@email.com")]')) == 1

    def test_should_show_error_message_if_no_signed_url(self, s3):
        with mock.patch('app.main.views.suppliers.get_signed_url') as mock_get_url:
            mock_get_url.return_value = None
            response = self.client.get('/admin/suppliers/1234/agreements/g-cloud-8')
            assert response.status_code == 200
            assert 'Agreement file not available' in response.get_data(as_text=True)

    def test_should_embed_for_pdf_file(self, s3):
        with mock.patch('app.main.views.suppliers.get_signed_url') as mock_get_url:
            mock_get_url.return_value = "http://example.com/document/1234.pdf"
            response = self.client.get('/admin/suppliers/1234/agreements/g-cloud-8')
            document = html.fromstring(response.get_data(as_text=True))
            assert response.status_code == 200
            assert len(document.xpath('//embed[@src="http://example.com/document/1234.pdf"]')) == 1
            assert len(document.xpath('//img[@src="http://example.com/document/1234.pdf"]')) == 0

    def test_should_img_for_image_file(self, s3):
        supplier_framework_info = self.load_example_listing(
            'supplier_framework_response'
        )
        supplier_framework_info['frameworkInterest']['agreementPath'] = 'path/to/img.jpg'
        self.data_api_client.get_supplier_framework_info.return_value = supplier_framework_info

        with mock.patch('app.main.views.suppliers.get_signed_url') as mock_get_url:
            mock_get_url.return_value = "http://example.com/document/1234.png"
            response = self.client.get('/admin/suppliers/1234/agreements/g-cloud-8')
            document = html.fromstring(response.get_data(as_text=True))
            assert response.status_code == 200
            assert len(document.xpath('//img[@src="http://example.com/document/1234.png"]')) == 1
            assert len(document.xpath('//embed[@src="http://example.com/document/1234.png"]')) == 0

    @pytest.mark.parametrize("role, expected_code", [
        ("admin", 403),
        ("admin-ccs-category", 200),
        ("admin-ccs-sourcing", 200),
        ("admin-ccs-data-controller", 200),
        ("admin-framework-manager", 200),
        ("admin-manager", 403),
    ])
    def test_view_signed_agreement_accessible_to_specific_user_roles(self, s3, role, expected_code):
        self.user_role = role

        with mock.patch('app.main.views.suppliers.get_signed_url') as mock_get_url:
            mock_get_url.return_value = "http://example.com/document/1234.pdf"

            response = self.client.get('/admin/suppliers/1234/agreements/g-cloud-8')
            actual_code = response.status_code
            assert actual_code == expected_code, "Unexpected response {} for role {}".format(actual_code, role)


class TestPutSignedAgreementOnHold(LoggedInApplicationTest):
    user_role = 'admin-ccs-sourcing'

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.suppliers.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()
        self.data_api_client.put_signed_agreement_on_hold.return_value = self.put_signed_agreement_on_hold_return_value

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    @property
    def put_signed_agreement_on_hold_return_value(self):
        # a property so we always get a clean *copy* of this to work with
        return {
            "agreement": {
                "id": 123,
                "supplierId": 4321,
                "frameworkSlug": "g-cloud-99-flake",
            },
        }

    def test_it_fails_if_not_ccs_admin(self):
        self.user_role = 'admin'

        res = self.client.post('/admin/suppliers/agreements/123/on-hold', data={"nameOfOrganisation": "Test"})

        assert self.data_api_client.put_signed_agreement_on_hold.call_args_list == []
        assert res.status_code == 403

    def test_happy_path(self):
        res = self.client.post(
            "/admin/suppliers/agreements/123/on-hold",
            data={"nameOfOrganisation": "Test"},
        )

        self.data_api_client.put_signed_agreement_on_hold.assert_called_once_with('123', 'test@example.com')
        self.assert_flashes("The agreement for Test was put on hold.")
        assert res.status_code == 302

        parsed_location = urlparse(res.location)
        assert parsed_location.path == "/admin/suppliers/4321/agreements/g-cloud-99-flake/next"
        assert parse_qs(parsed_location.query) == {}

    def test_happy_path_with_next_status(self):
        res = self.client.post(
            "/admin/suppliers/agreements/123/on-hold?next_status=on-hold",
            data={"nameOfOrganisation": "Test"},
        )

        self.data_api_client.put_signed_agreement_on_hold.assert_called_once_with('123', 'test@example.com')
        self.assert_flashes("The agreement for Test was put on hold.")
        assert res.status_code == 302

        parsed_location = urlparse(res.location)
        assert parsed_location.path == "/admin/suppliers/4321/agreements/g-cloud-99-flake/next"
        assert parse_qs(parsed_location.query) == {"status": ["on-hold"]}


class TestApproveAgreement(LoggedInApplicationTest):
    user_role = 'admin-ccs-sourcing'

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.suppliers.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()
        self.data_api_client.approve_agreement_for_countersignature.return_value = {
            "agreement": {
                "id": 123,
                "supplierId": 4321,
                "frameworkSlug": "g-cloud-99p-world",
            },
        }

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    def test_it_fails_if_not_ccs_admin(self):
        self.user_role = 'admin'
        res = self.client.post('/admin/suppliers/agreements/123/approve', data={"nameOfOrganisation": "Test"})

        assert self.data_api_client.approve_agreement_for_countersignature.call_args_list == []
        assert res.status_code == 403

    def test_happy_path(self):
        res = self.client.post(
            "/admin/suppliers/agreements/123/approve",
            data={"nameOfOrganisation": "Test"},
        )

        self.data_api_client.approve_agreement_for_countersignature.assert_called_once_with(
            '123', 'test@example.com', '1234'
        )
        self.assert_flashes("The agreement for Test was approved. They will receive a countersigned version soon.")
        assert res.status_code == 302

        parsed_location = urlparse(res.location)
        assert parsed_location.path == "/admin/suppliers/4321/agreements/g-cloud-99p-world/next"
        assert parse_qs(parsed_location.query) == {}

    def test_happy_path_with_next_status_and_unicode_supplier_name(self):
        res = self.client.post(
            "/admin/suppliers/agreements/123/approve?next_status=on-hold",
            data={"nameOfOrganisation": u"Test O\u2019Connor"},
        )

        self.data_api_client.approve_agreement_for_countersignature.assert_called_once_with(
            '123', 'test@example.com', '1234'
        )
        self.assert_flashes(u"The agreement for Test O\u2019Connor was approved. They will receive a countersigned "
                            "version soon.")
        assert res.status_code == 302

        parsed_location = urlparse(res.location)
        assert parsed_location.path == "/admin/suppliers/4321/agreements/g-cloud-99p-world/next"
        assert parse_qs(parsed_location.query) == {"status": ["on-hold"]}


class TestUnapproveAgreement(LoggedInApplicationTest):
    user_role = 'admin-ccs-sourcing'

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.suppliers.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()
        self.data_api_client.unapprove_agreement_for_countersignature.return_value = {
            "agreement": {
                "id": 123,
                "supplierId": 4321,
                "frameworkSlug": "g-cloud-99p-world",
            },
        }

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    def test_it_fails_if_not_ccs_admin(self):
        self.user_role = 'admin'

        res = self.client.post('/admin/suppliers/agreements/123/unapprove', data={"nameOfOrganisation": "Test"})

        assert self.data_api_client.unapprove_agreement_for_countersignature.call_args_list == []
        assert res.status_code == 403

    def test_happy_path(self):
        res = self.client.post(
            "/admin/suppliers/agreements/123/unapprove",
            data={"nameOfOrganisation": "Test"},
        )

        self.data_api_client.unapprove_agreement_for_countersignature.assert_called_once_with(
            '123',
            'test@example.com',
            '1234',
        )
        self.assert_flashes("The agreement for Test had its approval cancelled. You can approve it again at any time.")
        assert res.status_code == 302

        parsed_location = urlparse(res.location)
        assert parsed_location.path == "/admin/suppliers/4321/agreements/g-cloud-99p-world"
        assert parse_qs(parsed_location.query) == {}

    def test_happy_path_with_next_status_and_unicode_supplier_name(self):
        res = self.client.post(
            "/admin/suppliers/agreements/123/unapprove?next_status=on-hold",
            data={"nameOfOrganisation": u"Test O\u2019Connor"},
        )

        self.data_api_client.unapprove_agreement_for_countersignature.assert_called_once_with(
            '123',
            'test@example.com',
            '1234',
        )
        self.assert_flashes(
            u"The agreement for Test O\u2019Connor had its approval cancelled. You can approve it again at any time.",
        )
        assert res.status_code == 302

        parsed_location = urlparse(res.location)
        assert parsed_location.path == "/admin/suppliers/4321/agreements/g-cloud-99p-world"
        assert parse_qs(parsed_location.query) == {"next_status": ["on-hold"]}


@mock.patch('app.main.views.suppliers.get_signed_url')
@mock.patch('app.main.views.suppliers.s3')
class TestCorrectButtonsAreShownDependingOnContext(LoggedInApplicationTest):
    user_role = 'admin-ccs-sourcing'

    decl_nameOfOrganization = u"\u00a3\u00a3\u00a3 4 greengrocer's"

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.suppliers.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()
        self.data_api_client.get_supplier.return_value = {
            'suppliers': {
                "id": 1234,
            },
        }
        self.data_api_client.get_framework.return_value = {
            'frameworks': {
                'frameworkAgreementVersion': 'v1.0',
                'slug': 'g-cloud-8',
                'status': 'live',
            },
        }
        self.data_api_client.find_services_iter.return_value = []

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    def set_mocks(self, s3, get_signed_url, **kwargs):
        self.data_api_client.get_supplier_framework_info.return_value = {
            'frameworkInterest': {
                'agreementReturned': True,
                'agreementStatus': kwargs['agreement_status'],
                'agreementId': 4321,
                'declaration': {
                    "nameOfOrganisation": self.decl_nameOfOrganization,
                },
                'agreementDetails': {},
                'agreementPath': 'g-cloud-8/1234/1234-file.pdf',
                'countersignedDetails': {},
                "supplierId": 1234,
                "frameworkSlug": "g-cloud-8",
            }
        }
        get_signed_url.return_value = '#'
        s3.S3.return_value.list.return_value = [
            {'path': 'g-cloud-8/agreements/4321/4321-signed-framework-agreement.png',
             'ext': 'pdf'}
        ]

    @staticmethod
    def _parsed_url_matches(url, path_matches=None, qd_matches=None):
        parsed_url = urlparse(url)
        return (
            path_matches is None or parsed_url.path == path_matches
        ) and (
            qd_matches is None or parse_qs(parsed_url.query) == qd_matches
        )

    @pytest.mark.parametrize("role, expected_code, read_only", [
        ("admin", 403, None),
        ("admin-ccs-category", 200, True),
        ("admin-ccs-sourcing", 200, False),
        ("admin-framework-manager", 200, True),
        ("admin-manager", 403, None),
    ])
    def test_get_page_should_only_be_accessible_to_specific_user_roles(
        self, s3, get_signed_url, role, expected_code, read_only
    ):
        self.user_role = role
        self.set_mocks(s3, get_signed_url, agreement_status='signed')
        response = self.client.get("/admin/suppliers/1234/agreements/g-cloud-8")
        actual_code = response.status_code
        assert actual_code == expected_code, "Unexpected response {} for role {}".format(actual_code, role)
        # No action buttons should be shown if read-only
        if read_only:
            document = html.fromstring(response.get_data(as_text=True))
            input_elems = document.xpath("//main//form//input[@type='submit']")
            assert len(input_elems) == 0

    @pytest.mark.parametrize("next_status", (None, "on-hold", "approved,countersigned",))
    def test_buttons_shown_if_ccs_admin_and_agreement_signed(self, s3, get_signed_url, next_status):
        self.set_mocks(s3, get_signed_url, agreement_status='signed')

        res = self.client.get("/admin/suppliers/1234/agreements/g-cloud-8{}".format(
            "" if next_status is None else "?next_status={}".format(next_status)
        ))
        assert res.status_code == 200

        data = res.get_data(as_text=True)
        document = html.fromstring(data)

        assert "Cancel acceptance" not in data

        accept_input_elems = document.xpath("//form//input[@type='submit'][@value='Accept and continue']")
        assert len(accept_input_elems) == 1
        accept_form_elem = accept_input_elems[0].xpath("ancestor::form")[0]
        assert self._parsed_url_matches(
            accept_form_elem.attrib["action"],
            "/admin/suppliers/agreements/4321/approve",
            {} if next_status is None else {"next_status": [next_status]},
        )
        assert accept_form_elem.attrib["method"].lower() == "post"
        assert accept_form_elem.xpath("input[@name='csrf_token']")
        assert accept_form_elem.xpath("input[@name='nameOfOrganisation'][@value=$n]", n=self.decl_nameOfOrganization)

        hold_input_elems = document.xpath("//form//input[@type='submit'][@value='Put on hold and continue']")
        assert len(hold_input_elems) == 1
        hold_form_elem = hold_input_elems[0].xpath("ancestor::form")[0]
        assert self._parsed_url_matches(
            hold_form_elem.attrib["action"],
            "/admin/suppliers/agreements/4321/on-hold",
            {} if next_status is None else {"next_status": [next_status]},
        )
        assert hold_form_elem.attrib["method"].lower() == "post"
        assert hold_form_elem.xpath("input[@name='csrf_token']")
        assert hold_form_elem.xpath("input[@name='nameOfOrganisation'][@value=$n]", n=self.decl_nameOfOrganization)

        assert not document.xpath("//h2[normalize-space(string())='Accepted by']")

        next_a_elems = document.xpath("//a[normalize-space(string())='Next agreement']")
        assert len(next_a_elems) == 1
        assert self._parsed_url_matches(
            next_a_elems[0].attrib["href"],
            "/admin/suppliers/1234/agreements/g-cloud-8/next",
            {} if next_status is None else {"status": [next_status]},
        )

        assert not document.xpath("//input[@type='submit'][contains(@value, 'Cancel')]")
        assert not document.xpath("//form[contains(@action, 'unapprove')]")

    @pytest.mark.parametrize("next_status", (None, "on-hold", "approved,countersigned",))
    def test_only_counter_sign_shown_if_agreement_on_hold(self, s3, get_signed_url, next_status):
        self.set_mocks(s3, get_signed_url, agreement_status='on-hold')

        res = self.client.get("/admin/suppliers/1234/agreements/g-cloud-8{}".format(
            "" if next_status is None else "?next_status={}".format(next_status)
        ))
        assert res.status_code == 200

        data = res.get_data(as_text=True)
        document = html.fromstring(data)

        assert "Cancel acceptance" not in data

        accept_input_elems = document.xpath("//form//input[@type='submit'][@value='Accept and continue']")
        assert len(accept_input_elems) == 1
        accept_form_elem = accept_input_elems[0].xpath("ancestor::form")[0]
        assert self._parsed_url_matches(
            accept_form_elem.attrib["action"],
            "/admin/suppliers/agreements/4321/approve",
            {} if next_status is None else {"next_status": [next_status]},
        )
        assert accept_form_elem.attrib["method"].lower() == "post"
        assert accept_form_elem.xpath("input[@name='csrf_token']")
        assert accept_form_elem.xpath("input[@name='nameOfOrganisation'][@value=$n]", n=self.decl_nameOfOrganization)

        assert "Put on hold and continue" not in data
        assert not document.xpath("//h2[normalize-space(string())='Accepted by']")

        next_a_elems = document.xpath("//a[normalize-space(string())='Next agreement']")
        assert len(next_a_elems) == 1
        assert self._parsed_url_matches(
            next_a_elems[0].attrib["href"],
            "/admin/suppliers/1234/agreements/g-cloud-8/next",
            {} if next_status is None else {"status": [next_status]},
        )

        assert not document.xpath("//input[@type='submit'][contains(@value, 'Cancel')]")
        assert not document.xpath("//form[contains(@action, 'unapprove')]")

    @pytest.mark.parametrize("next_status", (None, "on-hold", "approved,countersigned",))
    def test_cancel_shown_if_agreement_approved(self, s3, get_signed_url, next_status):
        self.set_mocks(s3, get_signed_url, agreement_status='approved')

        res = self.client.get("/admin/suppliers/1234/agreements/g-cloud-8{}".format(
            "" if next_status is None else "?next_status={}".format(next_status)
        ))
        assert res.status_code == 200

        data = res.get_data(as_text=True)
        document = html.fromstring(data)

        assert "Accept and continue" not in data
        assert "Put on hold and continue" not in data
        assert len(document.xpath("//h2[normalize-space(string())='Accepted by']")) == 1

        cancel_input_elems = document.xpath("//form//input[@type='submit'][@value='Cancel acceptance']")
        assert len(cancel_input_elems) == 1
        cancel_form_elem = cancel_input_elems[0].xpath("ancestor::form")[0]
        assert self._parsed_url_matches(
            cancel_form_elem.attrib["action"],
            "/admin/suppliers/agreements/4321/unapprove",
            {} if next_status is None else {"next_status": [next_status]},
        )
        assert cancel_form_elem.attrib["method"].lower() == "post"
        assert cancel_form_elem.xpath("input[@name='csrf_token']")
        assert cancel_form_elem.xpath("input[@name='nameOfOrganisation'][@value=$n]", n=self.decl_nameOfOrganization)

        next_a_elems = document.xpath("//a[normalize-space(string())='Next agreement']")
        assert len(next_a_elems) == 1
        assert self._parsed_url_matches(
            next_a_elems[0].attrib["href"],
            "/admin/suppliers/1234/agreements/g-cloud-8/next",
            {} if next_status is None else {"status": [next_status]},
        )

    @pytest.mark.parametrize("next_status", (None, "on-hold", "approved,countersigned",))
    def test_none_shown_if_agreement_countersigned(self, s3, get_signed_url, next_status):
        self.set_mocks(s3, get_signed_url, agreement_status='countersigned')

        res = self.client.get("/admin/suppliers/1234/agreements/g-cloud-8{}".format(
            "" if next_status is None else "?next_status={}".format(next_status)
        ))
        assert res.status_code == 200

        data = res.get_data(as_text=True)
        document = html.fromstring(data)

        assert "Accept and continue" not in data
        assert "Put on hold and continue" not in data
        assert "Cancel acceptance" not in data
        assert len(document.xpath("//h2[normalize-space(string())='Accepted by']")) == 1

        next_a_elems = document.xpath("//a[normalize-space(string())='Next agreement']")
        assert len(next_a_elems) == 1
        assert self._parsed_url_matches(
            next_a_elems[0].attrib["href"],
            "/admin/suppliers/1234/agreements/g-cloud-8/next",
            {} if next_status is None else {"status": [next_status]},
        )

        assert not document.xpath("//input[@type='submit'][contains(@value, 'Cancel')]")
        assert not document.xpath("//form[contains(@action, 'unapprove')]")
