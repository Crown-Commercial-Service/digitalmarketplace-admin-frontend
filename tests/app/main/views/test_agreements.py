from itertools import chain

import mock
from lxml import html
from nose.tools import eq_
from six import iteritems, iterkeys
from six.moves.urllib.parse import urlparse, urlunparse, parse_qs

from app.main.views.agreements import status_labels
from ...helpers import LoggedInApplicationTest


@mock.patch('app.main.views.agreements.data_api_client')
class TestListAgreements(LoggedInApplicationTest):
    user_role = 'admin-ccs-sourcing'

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
                },
                {
                    'supplierName': 'My Supplier',
                    'supplierId': 11111,
                    'agreementReturned': True,
                    'agreementReturnedAt': '2015-11-01T01:01:01.000000Z',
                    'agreementPath': 'path/11111-agreement.pdf',
                    'frameworkSlug': 'g-cloud-8',
                },
            ],
        }

    def test_happy_path(self, data_api_client):
        data_api_client.get_framework.return_value = self.load_example_listing('framework_response')
        data_api_client.find_framework_suppliers.return_value = {
            'supplierFrameworks': [
                {
                    'supplierName': 'My Supplier',
                    'supplierId': 11111,
                    'agreementReturned': True,
                    'agreementReturnedAt': '2015-11-01T01:01:01.000000Z',
                    'agreementPath': 'path/11111-agreement.pdf',
                },
                {
                    'supplierName': 'My other supplier',
                    'supplierId': 11112,
                    'agreementReturned': True,
                    'agreementReturnedAt': '2015-10-30T01:01:01.000000Z',
                    'agreementPath': 'path/11112-agreement.pdf',
                },
            ]
        }

        response = self.client.get('/admin/agreements/g-cloud-7')
        page = html.fromstring(response.get_data(as_text=True))

        eq_(response.status_code, 200)
        rows = page.cssselect('.summary-item-row')
        eq_(len(rows), 2)

    @staticmethod
    def _unpack_search_result(elem):
        a_elems = elem.cssselect(".search-result-title a")
        assert len(a_elems) == 1
        mi_elems = elem.cssselect(".search-result-metadata-item")
        assert len(mi_elems) == 1
        return (
            urlunparse(("", "",) + urlparse(a_elems[0].attrib["href"])[2:]),
            a_elems[0].xpath("normalize-space(string())"),
            mi_elems[0].xpath("normalize-space(string())"),
        )

    def test_happy_path_all_g8(self, data_api_client):
        data_api_client.get_framework.return_value = self.load_example_listing('framework_response')
        data_api_client.find_framework_suppliers.return_value = self.find_framework_suppliers_return_value_g8

        response = self.client.get('/admin/agreements/g-cloud-8')
        page = html.fromstring(response.get_data(as_text=True))

        assert response.status_code == 200

        call_args = data_api_client.find_framework_suppliers.call_args
        assert call_args[0] == ("g-cloud-8",)
        # slightly elaborate assertion here to allow for missing kwargs defaulting to None
        assert all(call_args[1].get(key) == value for key, value in (
            ("agreement_returned", True),
            ("statuses", None),
        ))

        assert tuple(self._unpack_search_result(result) for result in page.cssselect('.search-result')) == (
            (
                "/admin/suppliers/11112/agreements/g-cloud-8",
                "My other supplier",
                "Submitted: Friday 30 October 2015 at 01:01",
            ),
            (
                "/admin/suppliers/11111/agreements/g-cloud-8",
                "My Supplier",
                "Submitted: Sunday 1 November 2015 at 01:01",
            ),
        )

        assert page.xpath("//*[@class='status-filters']//li[normalize-space(string())='All']")

        assert tuple(
            (parse_qs(urlparse(a_element.attrib["href"]).query), a_element.xpath("normalize-space(string())"))
            for a_element in page.cssselect('.status-filters a')
        ) == tuple(
            ({"status": [status_key]}, status_label)
            for status_key, status_label in iteritems(status_labels)
        )

    def test_happy_path_notall_g8(self, data_api_client):
        data_api_client.get_framework.return_value = self.load_example_listing('framework_response')
        data_api_client.find_framework_suppliers.return_value = self.find_framework_suppliers_return_value_g8

        # choose the second status (if there is one, otherwise first)
        chosen_status_key = tuple(iterkeys(status_labels))[:2][-1]

        response = self.client.get('/admin/agreements/g-cloud-8?status={}'.format(chosen_status_key))
        page = html.fromstring(response.get_data(as_text=True))

        assert response.status_code == 200

        call_args = data_api_client.find_framework_suppliers.call_args
        assert call_args[0] == ("g-cloud-8",)
        # slightly elaborate assertion here to allow for missing kwargs defaulting to None
        assert all(call_args[1].get(key) == value for key, value in (
            ("agreement_returned", True),
            ("statuses", chosen_status_key),
        ))

        assert tuple(self._unpack_search_result(result) for result in page.cssselect('.search-result')) == (
            (
                "/admin/suppliers/11112/agreements/g-cloud-8",
                "My other supplier",
                "Submitted: Friday 30 October 2015 at 01:01",
            ),
            (
                "/admin/suppliers/11111/agreements/g-cloud-8",
                "My Supplier",
                "Submitted: Sunday 1 November 2015 at 01:01",
            ),
        )

        assert any(
            # (don't really want to risk shoving unescaped text into the xpath query, so pulling the elements out and
            # comparing them in python)
            element.xpath("normalize-space(string())") == status_labels[chosen_status_key]
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
                for status_key, status_label in iteritems(status_labels) if status_key != chosen_status_key
            ),
        ))

    def test_unauthorised_roles_are_rejected_access(self, data_api_client):
        self.user_role = 'admin-ccs-category'

        response = self.client.get('/admin/agreements/g-cloud-7')

        eq_(response.status_code, 403)
