import mock
from lxml import html
from nose.tools import eq_

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
                },
                {
                    'supplierName': 'My other supplier',
                    'supplierId': 11112,
                    'agreementReturned': True,
                    'agreementReturnedAt': '2015-10-30T01:01:01.000000Z',
                },
            ]
        }

        response = self.client.get('/admin/agreements/g-cloud-7')
        page = html.fromstring(response.get_data(as_text=True))

        eq_(response.status_code, 200)
        rows = page.cssselect('.summary-item-row')
        eq_(len(rows), 2)

    def test_unauthorised_roles_are_rejected_access(self, data_api_client):
        self.user_role = 'admin-ccs-category'

        response = self.client.get('/admin/agreements/g-cloud-7')

        eq_(response.status_code, 403)
