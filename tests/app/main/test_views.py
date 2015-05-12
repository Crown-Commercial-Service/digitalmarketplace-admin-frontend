try:
    from urlparse import urlsplit
    from StringIO import StringIO
except ImportError:
    from urllib.parse import urlsplit
    from io import BytesIO as StringIO

import mock
from dmutils.apiclient import APIError

from ..helpers import BaseApplicationTest
from ..helpers import LoggedInApplicationTest


class TestSession(BaseApplicationTest):
    def test_index(self):
        response = self.client.get('/admin/')
        self.assertEquals(302, response.status_code)

    def test_login(self):
        response = self.client.post('/admin/login', data=dict(
            username="admin",
            password="admin"
        ))
        self.assertEquals(302, response.status_code)
        self.assertEquals("/admin/", urlsplit(response.location).path)

        response = self.client.get('/admin/')
        self.assertEquals(200, response.status_code)

    def test_invalid_login(self):
        response = self.client.post('/admin/login', data=dict(
            username="admin",
            password="wrong"
        ))
        self.assertEquals(200, response.status_code)

        response = self.client.get('/admin/')
        self.assertEquals(302, response.status_code)
        self.assertEquals("/admin/login", urlsplit(response.location).path)


class TestApplication(LoggedInApplicationTest):
    def test_main_index(self):
        response = self.client.get('/admin/')
        self.assertEquals(200, response.status_code)

    def test_404(self):
        response = self.client.get('/admin/not-found')
        self.assertEquals(404, response.status_code)

    def test_index_is_404(self):
        response = self.client.get('/')
        self.assertEquals(404, response.status_code)


class TestServiceView(LoggedInApplicationTest):
    @mock.patch('app.main.views.data_api_client')
    def test_service_response(self, data_api_client):
        data_api_client.get_service.return_value = {}
        response = self.client.get('/admin/service/1')

        data_api_client.get_service.assert_called_with('1')

        self.assertEquals(200, response.status_code)

    @mock.patch('app.main.views.data_api_client')
    def test_responds_with_404_for_api_client_404(self, data_api_client):
        error = mock.Mock()
        error.response.status_code = 404
        data_api_client.get_service.side_effect = APIError(error)

        response = self.client.get('/admin/service/1')

        self.assertEquals(404, response.status_code)


class TestServiceEdit(LoggedInApplicationTest):
    @mock.patch('app.main.views.data_api_client')
    def test_service_edit_documents_get_response(self, data_api_client):
        response = self.client.get('/admin/service/1/edit/documents')

        data_api_client.get_service.assert_called_with('1')

        self.assertEquals(200, response.status_code)

    @mock.patch('app.main.views.data_api_client')
    def test_service_edit_documents_empty_post(self, data_api_client):
        data_api_client.get_service.return_value = {
            'id': 1,
            'supplierId': 2,
        }
        response = self.client.post(
            '/admin/service/1/edit/documents',
            data={}
        )

        data_api_client.get_service.assert_called_with('1')
        self.assertFalse(data_api_client.update_service.called)

        self.assertEquals(302, response.status_code)
        self.assertEquals("/admin/service/1", urlsplit(response.location).path)

    @mock.patch('app.main.views.data_api_client')
    def test_service_edit_documents_post(self, data_api_client):
        data_api_client.get_service.return_value = {
            'id': 1,
            'supplierId': 2,
            'pricingDocumentURL': "http://assets/documents/1/2-pricing.pdf",
            'serviceDefinitionDocumentURL': "http://assets/documents/1/2-service-definition.pdf",  # noqa
            'termsAndConditionsDocumentURL': "http://assets/documents/1/2-terms-and-conditions.pdf",  # noqa
            'sfiaRateDocumentURL': None
        }
        response = self.client.post(
            '/admin/service/1/edit/documents',
            data={
                'serviceDefinitionDocumentURL': (StringIO(), ''),
                'pricingDocumentURL': (StringIO(b"doc"), 'test.pdf'),
                'sfiaRateDocumentURL': (StringIO(b"doc"), 'test.pdf'),
                'termsAndConditionsDocumentURL': (StringIO(b''), ''),
            }
        )

        data_api_client.get_service.assert_called_with('1')
        data_api_client.update_service.assert_called_with(1, {
            'pricingDocumentURL': 'https://assets.test.digitalmarketplace.service.gov.uk/documents/2/1-pricing-document-2015-01-01-1200.pdf',  # noqa
            'sfiaRateDocumentURL': 'https://assets.test.digitalmarketplace.service.gov.uk/documents/2/1-sfia-rate-card-2015-01-01-1200.pdf',  # noqa
        }, 'admin', 'admin app')

        self.assertEquals(302, response.status_code)

    @mock.patch("app.main.views.data_api_client")
    def test_service_edit_documents_post_with_validation_errors(
            self, data_api_client):
        data_api_client.get_service.return_value = {
            'id': 1,
            'supplierId': 2,
            'lot': 'SCS',
            'serviceDefinitionDocumentURL': "http://assets/documents/1/2-service-definition.pdf",  # noqa
            'pricingDocumentURL': "http://assets/documents/1/2-pricing.pdf",
            'sfiaRateDocumentURL': None
        }
        response = self.client.post(
            '/admin/service/1/edit/documents',
            data={
                'serviceDefinitionDocumentURL': (StringIO(), ''),
                'pricingDocumentURL': (StringIO(b"doc"), 'test.pdf'),
                'sfiaRateDocumentURL': (StringIO(b"doc"), 'test.txt'),
                'termsAndConditionsDocumentURL': (StringIO(), 'test.pdf'),
            }
        )

        data_api_client.get_service.assert_called_with('1')
        data_api_client.update_service.assert_called_with(1, {
            'pricingDocumentURL': 'https://assets.test.digitalmarketplace.service.gov.uk/documents/2/1-pricing-document-2015-01-01-1200.pdf',  # noqa
        }, 'admin', 'admin app')

        self.assertIn(b'Your document is not in an open format', response.data)
        self.assertIn(b'This question requires an answer', response.data)
        self.assertEquals(200, response.status_code)

    @mock.patch('app.main.views.data_api_client')
    def test_service_edit_when_API_returns_error(self, data_api_client):
        data_api_client.get_service.return_value = {
            'id': 1,
            'supplierId': 2,
            'pricingDocumentURL': "http://assets/documents/1/2-pricing.pdf",
            'sfiaRateDocumentURL': None
        }
        error = mock.Mock()
        error.response.content = "API ERROR"
        data_api_client.update_service.side_effect = APIError(error)

        response = self.client.post(
            '/admin/service/1/edit/documents',
            data={
                'pricingDocumentURL': (StringIO(b"doc"), 'test.pdf'),
                'sfiaRateDocumentURL': (StringIO(b"doc"), 'test.txt'),
                'termsAndConditionsDocumentURL': (StringIO(), 'test.pdf'),
            }
        )
        self.assertIn(b'API ERROR', response.data)
