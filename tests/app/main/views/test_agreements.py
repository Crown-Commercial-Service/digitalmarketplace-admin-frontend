import mock
from lxml import html
from nose.tools import eq_
from six.moves.urllib.parse import urlparse, urlunparse

from ...helpers import LoggedInApplicationTest


@mock.patch('app.main.views.agreements.data_api_client')
class TestListAgreements(LoggedInApplicationTest):
    user_role = 'admin-ccs-sourcing'

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
    def _unpack_single_a_elem(elems):
        assert len(elems) == 1
        return urlunparse(("", "",) + urlparse(elems[0].attrib["href"])[2:]), elems[0].text

    def test_happy_path_g8(self, data_api_client):
        data_api_client.get_framework.return_value = self.load_example_listing('framework_response')
        data_api_client.find_framework_suppliers.return_value = {
            'supplierFrameworks': [
                {
                    'supplierName': 'My other supplier',
                    'supplierId': 11112,
                    'agreementReturned': True,
                    'agreementReturnedAt': '2015-10-30T01:01:01.000000Z',
                    'frameworkSlug': 'g-cloud-8',
                },
                {
                    'supplierName': 'My Supplier',
                    'supplierId': 11111,
                    'agreementReturned': True,
                    'agreementReturnedAt': '2015-11-01T01:01:01.000000Z',
                    'frameworkSlug': 'g-cloud-8',
                },
            ],
        }

        response = self.client.get('/admin/agreements/g-cloud-8')
        page = html.fromstring(response.get_data(as_text=True))

        assert response.status_code == 200
        rows = page.cssselect('.search-result')

        def unpack_search_result(elem):
            a_elems = elem.cssselect(".search-result-title a")
            assert len(a_elems) == 1
            mi_elems = elem.cssselect(".search-result-metadata-item")
            assert len(mi_elems) == 1
            return (
                urlunparse(("", "",) + urlparse(a_elems[0].attrib["href"])[2:]),
                a_elems[0].text.strip(),
                mi_elems[0].text.strip(),
            )
        assert tuple(unpack_search_result(result) for result in page.cssselect('.search-result')) == (
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

    def test_unauthorised_roles_are_rejected_access(self, data_api_client):
        self.user_role = 'admin-ccs-category'

        response = self.client.get('/admin/agreements/g-cloud-7')

        eq_(response.status_code, 403)
