from itertools import chain
from urllib.parse import urlparse, parse_qs

import mock
import pytest
from lxml import html

from app.main.views.agreements import get_status_labels
from ...helpers import LoggedInApplicationTest


class TestListAgreements(LoggedInApplicationTest):
    user_role = 'admin-ccs-sourcing'

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.agreements.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()
        self.status_labels = get_status_labels()

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    @property
    def find_framework_suppliers_return_value_g8(self):
        # a property so we always get a fresh *copy* of this
        return {
            'supplierFrameworks': [
                {
                    'supplierName': 'My other supplier',
                    'supplierId': 11112,
                    'agreementReturned': True,
                    'agreementReturnedAt': '2015-10-30T01:01:01.000000Z',
                    'agreementPath': 'path/11112-agreement.pdf',
                    'frameworkSlug': 'g-cloud-8',
                    'onFramework': True
                },
                {
                    'supplierName': 'My Supplier',
                    'supplierId': 11111,
                    'agreementReturned': True,
                    'agreementReturnedAt': '2015-11-01T01:01:01.000000Z',
                    'agreementPath': 'path/11111-agreement.pdf',
                    'frameworkSlug': 'g-cloud-8',
                    'onFramework': True
                },
                {
                    'supplierName': 'My Supplier no longer on framework',
                    'supplierId': 11111,
                    'agreementReturned': True,
                    'agreementReturnedAt': '2015-11-01T01:01:01.000000Z',
                    'agreementPath': 'path/11111-agreement.pdf',
                    'onFramework': False
                },
            ],
        }

    def test_happy_path(self):
        self.data_api_client.get_framework.return_value = {
            "frameworks": {
                "status": "live",
                "name": "G-Cloud 7",
                "slug": "g-cloud-7",
                "framework": "g-cloud",
                "isESignatureSupported": False
            }
        }

        self.data_api_client.find_framework_suppliers.return_value = {
            'supplierFrameworks': [
                {
                    'supplierName': 'My other supplier',
                    'supplierId': 11112,
                    'agreementReturned': True,
                    'agreementReturnedAt': '2015-10-30T01:01:01.000000Z',
                    'agreementPath': 'path/11112-agreement.pdf',
                    'onFramework': True
                },
                {
                    'supplierName': 'My Supplier',
                    'supplierId': 11111,
                    'agreementReturned': True,
                    'agreementReturnedAt': '2015-11-01T01:01:01.000000Z',
                    'agreementPath': 'path/11111-agreement.pdf',
                    'onFramework': True
                },
            ]
        }

        response = self.client.get('/admin/agreements/g-cloud-7')
        page = html.fromstring(response.get_data(as_text=True))
        assert response.status_code == 200
        rows = page.cssselect('.summary-item-row')
        assert len(rows) == 2

    @staticmethod
    def _unpack_search_result(elem):
        a_elems = elem.cssselect(".search-result-title a")
        assert len(a_elems) == 1
        mi_elems = elem.cssselect(".search-result-metadata-item")
        assert len(mi_elems) == 1
        parsed_href = urlparse(a_elems[0].attrib["href"])
        return (
            parsed_href.path,
            parse_qs(parsed_href.query),
            a_elems[0].xpath("normalize-space(string())"),
            mi_elems[0].xpath("normalize-space(string())"),
        )

    def test_happy_path_all_g8(self):
        self.data_api_client.get_framework.return_value = self.load_example_listing('framework_response')
        self.data_api_client.find_framework_suppliers.return_value = self.find_framework_suppliers_return_value_g8

        response = self.client.get('/admin/agreements/g-cloud-8')
        page = html.fromstring(response.get_data(as_text=True))

        assert response.status_code == 200

        call_args = self.data_api_client.find_framework_suppliers.call_args
        assert call_args[0] == ("g-cloud-8",)
        # slightly elaborate assertion here to allow for missing kwargs defaulting to None
        assert all(call_args[1].get(key) == value for key, value in (
            ("agreement_returned", True),
            ("statuses", None),
            ("with_declarations", False),
        ))

        # only suppliers who are on the framework are shown in the results list
        assert tuple(self._unpack_search_result(result) for result in page.cssselect('.search-result')) == (
            (
                "/admin/suppliers/11112/agreements/g-cloud-8",
                {},
                "My other supplier",
                "Submitted: Friday 30 October 2015 at 1:01am GMT",
            ),
            (
                "/admin/suppliers/11111/agreements/g-cloud-8",
                {},
                "My Supplier",
                "Submitted: Sunday 1 November 2015 at 1:01am GMT",
            ),
        )

        assert page.xpath("//*[@class='status-filters']//li[normalize-space(string())='All']")

        assert tuple(
            (parse_qs(urlparse(a_element.attrib["href"]).query), a_element.xpath("normalize-space(string())"))
            for a_element in page.cssselect('.status-filters a')
        ) == tuple(
            ({"status": [status_key]}, status_label)
            for status_key, status_label in self.status_labels.items()
        )

        summary_elem = page.xpath("//p[@class='govuk-body search-summary-border-bottom']")[0]
        assert summary_elem.xpath("normalize-space(string())") == '2 agreements returned'

    def test_happy_path_notall_g8(self):
        self.data_api_client.get_framework.return_value = self.load_example_listing('framework_response')
        find_framework_suppliers_return_value_g8 = self.find_framework_suppliers_return_value_g8
        # deliberately returning supplierFrameworks this time in "wrong" order to test view isn't doing any re-sorting
        find_framework_suppliers_return_value_g8["supplierFrameworks"].reverse()
        self.data_api_client.find_framework_suppliers.return_value = find_framework_suppliers_return_value_g8

        # choose the second status (if there is one, otherwise first)
        chosen_status_key = tuple(self.status_labels.keys())[:2][-1]

        response = self.client.get('/admin/agreements/g-cloud-8?status={}'.format(chosen_status_key))
        page = html.fromstring(response.get_data(as_text=True))

        assert response.status_code == 200

        call_args = self.data_api_client.find_framework_suppliers.call_args
        assert call_args[0] == ("g-cloud-8",)
        # slightly elaborate assertion here to allow for missing kwargs defaulting to None
        assert all(call_args[1].get(key) == value for key, value in (
            ("agreement_returned", True),
            ("statuses", chosen_status_key),
            ("with_declarations", False),
        ))

        assert tuple(self._unpack_search_result(result) for result in page.cssselect('.search-result')) == (
            (
                "/admin/suppliers/11111/agreements/g-cloud-8",
                {"next_status": [chosen_status_key]},
                "My Supplier",
                "Submitted: Sunday 1 November 2015 at 1:01am GMT",
            ),
            (
                "/admin/suppliers/11112/agreements/g-cloud-8",
                {"next_status": [chosen_status_key]},
                "My other supplier",
                "Submitted: Friday 30 October 2015 at 1:01am GMT",
            ),
        )

        assert any(
            # (don't really want to risk shoving unescaped text into the xpath query, so pulling the elements out and
            # comparing them in python)
            element.xpath("normalize-space(string())") == self.status_labels[chosen_status_key]
            for element in page.xpath("//*[@class='status-filters']//li")
        )

        assert tuple(
            (parse_qs(urlparse(a_element.attrib["href"]).query), a_element.xpath("normalize-space(string())"))
            for a_element in page.cssselect('.status-filters a')
        ) == tuple(chain(
            (
                ({}, "All",),
            ),
            (
                ({"status": [status_key]}, status_label)
                for status_key, status_label in self.status_labels.items() if status_key != chosen_status_key
            ),
        ))

        summary_elem = page.xpath("//p[@class='govuk-body search-summary-border-bottom']")[0]
        assert summary_elem.xpath("normalize-space(string())") == '2 agreements {}'.format(
            self.status_labels[chosen_status_key].lower()
        )

    def test_list_agreements_esignature_frameworks(self):
        self.data_api_client.get_framework.return_value = {
            "frameworks": {
                "slug": "g-cloud-12",
                "frameworkAgreementVersion": "RM.12",
                "isESignatureSupported": True
            }
        }
        self.data_api_client.find_framework_suppliers.return_value = {
            'supplierFrameworks': [
                {
                    'supplierName': 'My other supplier',
                    'supplierId': 11112,
                    'agreementReturned': True,
                    'agreementReturnedAt': '2020-10-30T01:01:01.000000Z',
                    'frameworkSlug': 'g-cloud-12',
                    'onFramework': True
                }
            ]
        }

        response = self.client.get('/admin/agreements/g-cloud-12?status=signed')
        page = html.fromstring(response.get_data(as_text=True))

        assert response.status_code == 200

        assert self.data_api_client.find_framework_suppliers.call_args_list == [
            mock.call('g-cloud-12', agreement_returned=True, statuses="signed", with_declarations=False)
        ]
        assert page.xpath('//h2[@class="search-result-title"]//a')[0].text.strip() == "My other supplier"

        summary_elem = page.xpath("//p[@class='govuk-body search-summary-border-bottom']")[0]
        assert summary_elem.xpath("normalize-space(string())") == '1 agreement waiting for automated countersigning'

    def test_list_agreements_esignature_frameworks_countersigned(self):
        self.data_api_client.get_framework.return_value = {
            "frameworks": {
                "slug": "g-cloud-12",
                "frameworkAgreementVersion": "RM.12",
                "isESignatureSupported": True
            }
        }
        self.data_api_client.find_framework_suppliers.return_value = {
            'supplierFrameworks': [
                {
                    'supplierName': 'My other supplier',
                    'supplierId': 11112,
                    'agreementReturned': True,
                    'agreementReturnedAt': '2020-10-30T01:01:01.000000Z',
                    'countersignedPath': 'path/11112-countersigned-agreement.pdf',
                    'frameworkSlug': 'g-cloud-12',
                    'onFramework': True
                }
            ]
        }

        response = self.client.get('/admin/agreements/g-cloud-12?status=approved,countersigned')
        page = html.fromstring(response.get_data(as_text=True))

        assert response.status_code == 200

        assert self.data_api_client.find_framework_suppliers.call_args_list == [
            mock.call('g-cloud-12', agreement_returned=True, statuses="approved,countersigned", with_declarations=False)
        ]
        assert page.xpath('//h2[@class="search-result-title"]//a')[0].text.strip() == "My other supplier"

        summary_elem = page.xpath("//p[@class='govuk-body search-summary-border-bottom']")[0]
        assert summary_elem.xpath("normalize-space(string())") == '1 agreement countersigned'

    @pytest.mark.parametrize("role,expected_code", [
        ("admin", 403),
        ("admin-ccs-category", 200),
        ("admin-ccs-sourcing", 200),
        ("admin-ccs-data-controller", 200),
        ("admin-framework-manager", 200),
        ("admin-manager", 403),
    ])
    def test_list_agreements_is_only_accessible_to_specific_user_roles(self, role, expected_code):
        self.user_role = role
        response = self.client.get('/admin/agreements/g-cloud-7')
        actual_code = response.status_code
        assert actual_code == expected_code, "Unexpected response {} for role {}".format(actual_code, role)

    def test_invalid_status_raises_400(self):
        response = self.client.get('/admin/agreements/g-cloud-7?status=bad')
        assert response.status_code == 400


class TestNextAgreementRedirect(LoggedInApplicationTest):
    user_role = 'admin-ccs-sourcing'

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.agreements.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()

        self.data_api_client.find_framework_suppliers.return_value = self.dummy_supplier_frameworks

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    @property
    def dummy_supplier_frameworks(self):
        # a property so we ensure we get a new clone every time we request it
        return {
            "supplierFrameworks": [
                {
                    "supplierId": 4321,
                    "frameworkSlug": "g-cloud-8",
                    "agreementStatus": "signed",
                    'onFramework': True
                },
                {
                    "supplierId": 1234,
                    "frameworkSlug": "g-cloud-8",
                    "agreementStatus": "on-hold",
                    'onFramework': True
                },
                {
                    "supplierId": 31415,
                    "frameworkSlug": "g-cloud-8",
                    "agreementStatus": "signed",
                    'onFramework': True
                },
                {
                    "supplierId": 27,
                    "frameworkSlug": "g-cloud-8",
                    "agreementStatus": "signed",
                    'onFramework': True
                },
                {
                    "supplierId": 141,
                    "frameworkSlug": "g-cloud-8",
                    "agreementStatus": "countersigned",
                    'onFramework': True
                },
                {
                    "supplierId": 151,
                    "frameworkSlug": "g-cloud-8",
                    "agreementStatus": "on-hold",
                    'onFramework': True
                },
                {
                    "supplierId": 99,
                    "frameworkSlug": "g-cloud-8",
                    "agreementStatus": "approved",
                    'onFramework': True
                },
            ],
        }

    def test_happy_path(self):
        res = self.client.get('/admin/suppliers/1234/agreements/g-cloud-8/next')
        assert res.status_code == 302

        parsed_location = urlparse(res.location)
        assert parsed_location.path == "/admin/suppliers/31415/agreements/g-cloud-8"
        assert parse_qs(parsed_location.query) == {}

    def test_unknown_supplier_returns_404(self):
        res = self.client.get('/admin/suppliers/999/agreements/g-cloud-8/next')
        assert res.status_code == 404

    def test_final_supplier_redirects_to_list(self):
        res = self.client.get('/admin/suppliers/99/agreements/g-cloud-8/next')
        assert res.status_code == 302

        parsed_location = urlparse(res.location)
        assert parsed_location.path == "/admin/agreements/g-cloud-8"
        assert parse_qs(parsed_location.query) == {}

    def test_status_filtered_simple_status(self):
        res = self.client.get('/admin/suppliers/1234/agreements/g-cloud-8/next?status=on-hold')
        assert res.status_code == 302

        parsed_location = urlparse(res.location)
        assert parsed_location.path == "/admin/suppliers/151/agreements/g-cloud-8"
        assert parse_qs(parsed_location.query) == {"next_status": ["on-hold"]}

        # if there weren't any non-status-filtering find_framework_suppliers calls, the view won't have been able to
        # get it right. should also be conserving bandwidth by omitting declarations.
        assert any(
            (ca_kwargs.get("with_declarations") is False and not ca_kwargs.get("status"))
            for ca_args, ca_kwargs in self.data_api_client.find_framework_suppliers.call_args_list
        )

    def test_status_filtered_compound_status(self):
        res = self.client.get('/admin/suppliers/141/agreements/g-cloud-8/next?status=approved,countersigned')
        assert res.status_code == 302

        parsed_location = urlparse(res.location)
        assert parsed_location.path == "/admin/suppliers/99/agreements/g-cloud-8"
        assert parse_qs(parsed_location.query) == {"next_status": ["approved,countersigned"]}

        # if there weren't any non-status-filtering find_framework_suppliers calls, the view won't have been able to
        # get it right. should also be conserving bandwidth by omitting declarations.
        assert any(
            (ca_kwargs.get("with_declarations") is False and not ca_kwargs.get("status"))
            for ca_args, ca_kwargs in self.data_api_client.find_framework_suppliers.call_args_list
        )

    def test_status_filtered_different_status_supplier(self):
        res = self.client.get('/admin/suppliers/1234/agreements/g-cloud-8/next?status=signed')
        assert res.status_code == 302

        parsed_location = urlparse(res.location)
        assert parsed_location.path == "/admin/suppliers/31415/agreements/g-cloud-8"
        assert parse_qs(parsed_location.query) == {"next_status": ["signed"]}

        # if there weren't any non-status-filtering find_framework_suppliers calls, the view won't have been able to
        # get it right. should also be conserving bandwidth by omitting declarations.
        assert any(
            (ca_kwargs.get("with_declarations") is False and not ca_kwargs.get("status"))
            for ca_args, ca_kwargs in self.data_api_client.find_framework_suppliers.call_args_list
        )

    def test_status_filtered_final_with_status_redirects_to_list(self):
        res = self.client.get('/admin/suppliers/151/agreements/g-cloud-8/next?status=on-hold')
        assert res.status_code == 302

        parsed_location = urlparse(res.location)
        assert parsed_location.path == "/admin/agreements/g-cloud-8"
        assert parse_qs(parsed_location.query) == {"status": ["on-hold"]}

        # if there weren't any non-status-filtering find_framework_suppliers calls, the view won't have been able to
        # get it right. should also be conserving bandwidth by omitting declarations.
        assert any(
            (ca_kwargs.get("with_declarations") is False and not ca_kwargs.get("status"))
            for ca_args, ca_kwargs in self.data_api_client.find_framework_suppliers.call_args_list
        )

    def test_invalid_status_raises_400(self):
        response = self.client.get('/admin/suppliers/151/agreements/g-cloud-8/next?status=bad')
        assert response.status_code == 400

    @pytest.mark.parametrize("role,expected_code", [
        ("admin", 403),
        ("admin-ccs-category", 302),
        ("admin-ccs-sourcing", 302),
        ("admin-ccs-data-controller", 302),
        ("admin-framework-manager", 302),
        ("admin-manager", 403),
    ])
    def test_next_agreement_redirect_only_accessible_to_specific_user_roles(self, role, expected_code):
        self.user_role = role
        response = self.client.get('/admin/suppliers/1234/agreements/g-cloud-8/next')
        actual_code = response.status_code
        assert actual_code == expected_code, "Unexpected response {} for role {}".format(actual_code, role)
