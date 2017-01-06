try:
    from urlparse import urlsplit
    from StringIO import StringIO
except ImportError:
    from urllib.parse import urlsplit
    from io import BytesIO as StringIO
import mock

from lxml import html

from dmapiclient import HTTPError, REQUEST_ERROR_MESSAGE
from ...helpers import LoggedInApplicationTest


class TestServiceView(LoggedInApplicationTest):
    @mock.patch('app.main.views.services.data_api_client')
    def test_service_view_no_features_or_benefits_status_disabled(self, data_api_client):
        data_api_client.get_service.return_value = {'services': {
            'frameworkSlug': 'g-cloud-8',
            'id': "314159265",
            "status": "disabled",
        }}
        response = self.client.get('/admin/services/314159265')

        assert data_api_client.get_service.call_args_list == [
            (("314159265",), {}),
        ]
        assert response.status_code == 200

        document = html.fromstring(response.get_data(as_text=True))
        assert document.xpath(
            "normalize-space(string(//td[@class='summary-item-field']//*[@class='service-id']))"
        ) == "314159265"

        assert frozenset(document.xpath("//input[@type='radio'][@name='service_status']/@value")) == frozenset((
            "removed",
            "private",
        ))
        assert document.xpath("//input[@type='radio'][@name='service_status'][@checked]/@value") == ["removed"]

    @mock.patch('app.main.views.services.data_api_client')
    def test_service_view_no_features_or_benefits_status_enabled(self, data_api_client):
        data_api_client.get_service.return_value = {'services': {
            'frameworkSlug': 'g-cloud-7',
            'id': "1412",
            "status": "enabled",
        }}
        response = self.client.get('/admin/services/1412')

        assert data_api_client.get_service.call_args_list == [
            (("1412",), {}),
        ]
        assert response.status_code == 200

        document = html.fromstring(response.get_data(as_text=True))
        assert document.xpath(
            "normalize-space(string(//td[@class='summary-item-field']//*[@class='service-id']))"
        ) == "1412"

        assert frozenset(document.xpath("//input[@type='radio'][@name='service_status']/@value")) == frozenset((
            "removed",
            "private",
            "public",
        ))
        assert document.xpath("//input[@type='radio'][@name='service_status'][@checked]/@value") == ["private"]

    @mock.patch('app.main.views.services.data_api_client')
    def test_service_view_no_features_or_benefits_not_service_status_authorized(self, data_api_client):
        self.user_role = "admin-ccs-category"
        data_api_client.get_service.return_value = {'services': {
            'frameworkSlug': 'g-cloud-7',
            'id': "271828",
            "status": "published",
        }}
        response = self.client.get('/admin/services/271828')

        assert data_api_client.get_service.call_args_list == [
            (("271828",), {}),
        ]
        assert response.status_code == 200

        document = html.fromstring(response.get_data(as_text=True))
        assert document.xpath(
            "normalize-space(string(//td[@class='summary-item-field']//*[@class='service-id']))"
        ) == "271828"

        # shouldn't be able to see this
        assert not document.xpath("//input[@name='service_status']")

    @mock.patch('app.main.views.services.data_api_client')
    def test_redirect_with_flash_for_api_client_404(self, data_api_client):
        response = mock.Mock()
        response.status_code = 404
        data_api_client.get_service.side_effect = HTTPError(response)

        response1 = self.client.get('/admin/services/1')
        assert response1.status_code == 302
        assert response1.location == 'http://localhost/admin'
        response2 = self.client.get(response1.location)
        assert b'Error trying to retrieve service with ID: 1' in response2.data

    @mock.patch('app.main.views.services.data_api_client')
    def test_service_not_found_flash_message_injection(self, data_api_client):
        """
        Asserts that raw HTML in a bad service ID cannot be injected into a flash message.
        """
        # impl copied from test_redirect_with_flash_for_api_client_404
        api_response = mock.Mock()
        api_response.status_code = 404
        data_api_client.get_service.side_effect = HTTPError(api_response)

        response1 = self.client.get('/admin/services/1%3Cimg%20src%3Da%20onerror%3Dalert%281%29%3E')
        response2 = self.client.get(response1.location)
        assert response2.status_code == 200

        html_response = response2.get_data(as_text=True)
        assert "1<img src=a onerror=alert(1)>" not in html_response
        assert "1&lt;img src=a onerror=alert(1)&gt;" in html_response

    @mock.patch('app.main.views.services.data_api_client')
    def test_independence_of_viewing_services(self, data_api_client):
        data_api_client.get_service.return_value = {'services': {
            'lot': 'SCS',
            'frameworkSlug': 'g-cloud-8',
            'id': "1",
        }}
        response = self.client.get('/admin/services/1')
        assert b'Termination cost' in response.data

        data_api_client.get_service.return_value = {'services': {
            'lot': 'SaaS',
            'frameworkSlug': 'g-cloud-8',
            'id': "1",
        }}
        response = self.client.get('/admin/services/1')
        assert b'Termination cost' not in response.data

        data_api_client.get_service.return_value = {'services': {
            'lot': 'SCS',
            'frameworkSlug': 'g-cloud-8',
            'id': "1",
        }}
        response = self.client.get('/admin/services/1')
        assert b'Termination cost' in response.data

    @mock.patch('app.main.views.services.data_api_client')
    def test_service_status_update_widgets_not_visible_when_not_permitted(self, data_api_client):
        data_api_client.get_service.return_value = {'services': {
            'lot': 'paas',
            'frameworkSlug': 'g-cloud-8',
            'id': "1",
        }}
        response = self.client.get('/admin/services/1')
        assert b'Termination cost' in response.data


class TestServiceEdit(LoggedInApplicationTest):
    @mock.patch('app.main.views.services.data_api_client')
    def test_edit_dos_service_title(self, data_api_client):
        data_api_client.get_service.return_value = {'services': {
            'frameworkSlug': 'digital-outcomes-and-specialists'
        }}
        response = self.client.get('/admin/services/1/edit/description')

        data_api_client.get_service.assert_called_with('1')

        assert response.status_code == 200

    @mock.patch('app.main.views.services.data_api_client')
    def test_service_edit_documents_get_response(self, data_api_client):
        data_api_client.get_service.return_value = {'services': {
            'frameworkSlug': 'g-cloud-8'
        }}
        response = self.client.get('/admin/services/1/edit/documents')

        data_api_client.get_service.assert_called_with('1')

        assert response.status_code == 200

    @mock.patch('app.main.views.services.data_api_client')
    def test_service_edit_documents_empty_post(self, data_api_client):
        data_api_client.get_service.return_value = {'services': {
            'id': 1,
            'supplierId': 2,
            'frameworkSlug': 'g-cloud-7',
            'lot': 'SCS',
            'serviceDefinitionDocumentURL': '',
            'termsAndConditionsDocumentURL': '',
            'sfiaRateDocumentURL': '',
            'pricingDocumentURL': '',
        }}
        response = self.client.post(
            '/admin/services/1/edit/documents',
            data={}
        )

        data_api_client.get_service.assert_called_with('1')
        assert data_api_client.update_service.called is False

        assert response.status_code == 302
        assert urlsplit(response.location).path == "/admin/services/1"

    @mock.patch('app.main.views.services.data_api_client')
    def test_service_edit_documents_post(self, data_api_client):
        data_api_client.get_service.return_value = {'services': {
            'id': 1,
            'supplierId': 2,
            'frameworkSlug': 'g-cloud-7',
            'lot': 'SCS',
            'pricingDocumentURL': "http://assets/documents/1/2-pricing.pdf",
            'serviceDefinitionDocumentURL': "http://assets/documents/1/2-service-definition.pdf",  # noqa
            'termsAndConditionsDocumentURL': "http://assets/documents/1/2-terms-and-conditions.pdf",  # noqa
            'sfiaRateDocumentURL': None
        }}
        response = self.client.post(
            '/admin/services/1/edit/documents',
            data={
                'serviceDefinitionDocumentURL': (StringIO(), ''),
                'pricingDocumentURL': (StringIO(b"doc"), 'test.pdf'),
                'sfiaRateDocumentURL': (StringIO(b"doc"), 'test.pdf'),
                'termsAndConditionsDocumentURL': (StringIO(b''), ''),
            }
        )

        data_api_client.get_service.assert_called_with('1')
        data_api_client.update_service.assert_called_with('1', {
            'pricingDocumentURL': 'https://assets.test.digitalmarketplace.service.gov.uk/g-cloud-7/documents/2/1-pricing-document-2015-01-01-1200.pdf',  # noqa
            'sfiaRateDocumentURL': 'https://assets.test.digitalmarketplace.service.gov.uk/g-cloud-7/documents/2/1-sfia-rate-card-2015-01-01-1200.pdf',  # noqa
        }, 'test@example.com')

        assert response.status_code == 302

    @mock.patch("app.main.views.services.data_api_client")
    def test_service_edit_documents_post_with_validation_errors(
            self, data_api_client):
        data_api_client.get_service.return_value = {'services': {
            'id': 1,
            'supplierId': 2,
            'frameworkSlug': 'g-cloud-7',
            'lot': 'SCS',
            'serviceDefinitionDocumentURL': "http://assets/documents/1/2-service-definition.pdf",  # noqa
            'pricingDocumentURL': "http://assets/documents/1/2-pricing.pdf",
            'sfiaRateDocumentURL': None
        }}
        response = self.client.post(
            '/admin/services/1/edit/documents',
            data={
                'serviceDefinitionDocumentURL': (StringIO(), ''),
                'pricingDocumentURL': (StringIO(b"doc"), 'test.pdf'),
                'sfiaRateDocumentURL': (StringIO(b"doc"), 'test.txt'),
                'termsAndConditionsDocumentURL': (StringIO(), 'test.pdf'),
            }
        )

        data_api_client.get_service.assert_called_with('1')
        assert data_api_client.update_service.called is False

        assert 'Your document is not in an open format' in response.get_data(as_text=True)
        assert response.status_code == 400

    @mock.patch('app.main.views.services.data_api_client')
    def test_service_edit_with_one_service_feature(self, data_api_client):
        data_api_client.get_service.return_value = {'services': {
            'id': 1,
            'supplierId': 2,
            'frameworkSlug': 'g-cloud-8',
            'lot': 'IaaS',
            'serviceFeatures': [
                "bar",
            ],
            'serviceBenefits': [
                "foo",
            ],
        }}
        response = self.client.get(
            '/admin/services/1/edit/features-and-benefits'
        )
        assert response.status_code == 200
        stripped_page = self.strip_all_whitespace(response.get_data(as_text=True))
        assert 'id="input-serviceFeatures-0"class="text-box"value="bar"' in stripped_page
        assert 'id="input-serviceFeatures-1"class="text-box"value=""' in stripped_page
        response = self.client.post(
            '/admin/services/1/edit/features-and-benefits',
            data={
                'serviceFeatures': 'foo',
                'serviceBenefits': 'foo',
            }
        )
        data_api_client.update_service.assert_called_with('1', {
            'serviceFeatures': ['foo'],
            'serviceBenefits': ['foo'],
        }, 'test@example.com')
        assert response.status_code == 302

    @mock.patch('app.main.views.services.data_api_client')
    def test_service_edit_with_no_features_or_benefits(self, data_api_client):
        data_api_client.get_service.return_value = {'services': {
            'lot': 'SaaS',
            'frameworkSlug': 'g-cloud-8',
        }}
        response = self.client.get(
            '/admin/services/1/edit/features-and-benefits')

        data_api_client.get_service.assert_called_with('1')

        assert response.status_code == 200
        assert 'id="input-serviceFeatures-0"class="text-box"value=""' in self.strip_all_whitespace(
            response.get_data(as_text=True)
        )

    @mock.patch('app.main.views.services.data_api_client')
    @mock.patch('app.main.views.services.upload_service_documents')
    def test_service_edit_when_API_returns_error(self, upload_service_documents, data_api_client):
        data_api_client.get_service.return_value = {'services': {
            'id': 1,
            'supplierId': 2,
            'lot': 'SCS',
            'frameworkSlug': 'g-cloud-7',
            'pricingDocumentURL': "http://assets/documents/1/2-pricing.pdf",
            'sfiaRateDocumentURL': None
        }}
        upload_service_documents.return_value = ({}, {})
        data_api_client.update_service.side_effect = HTTPError(None, {'sfiaRateDocumentURL': 'required'})

        response = self.client.post(
            '/admin/services/1/edit/documents',
            data={
                'pricingDocumentURL': (StringIO(b"doc"), 'test.pdf'),
                'sfiaRateDocumentURL': (StringIO(b"doc"), 'test.txt'),
                'termsAndConditionsDocumentURL': (StringIO(), 'test.pdf'),
            }
        )
        assert 'There was a problem with the answer to this question' in response.get_data(as_text=True)


@mock.patch('app.main.views.services.data_api_client')
class TestServiceStatusUpdate(LoggedInApplicationTest):

    def test_cannot_make_removed_service_public(self, data_api_client):
        data_api_client.get_service.return_value = {'services': {
            'id': 1,
            'frameworkSlug': 'g-cloud-8',
            'supplierId': 2,
            'status': 'disabled'
        }}
        response = self.client.get('/admin/services/1')
        assert b'<input type="radio" name="service_status" id="service_status_disabled" value="removed" checked="checked" />' in response.data  # noqa
        assert b'<input type="radio" name="service_status" id="service_status_private" value="private"  />' in response.data  # noqa
        assert b'<input type="radio" name="service_status" id="service_status_published" value="public"  />' not in response.data  # noqa

    def test_can_make_private_service_public_or_removed(self, data_api_client):
        data_api_client.get_service.return_value = {'services': {
            'id': 1,
            'frameworkSlug': 'g-cloud-8',
            'supplierId': 2,
            'status': 'enabled'
        }}
        response = self.client.get('/admin/services/1')
        assert b'<input type="radio" name="service_status" id="service_status_disabled" value="removed"  />' in response.data  # noqa
        assert b'<input type="radio" name="service_status" id="service_status_private" value="private" checked="checked" />' in response.data  # noqa
        assert b'<input type="radio" name="service_status" id="service_status_published" value="public"  />' in response.data  # noqa

    def test_can_make_public_service_private_or_removed(self, data_api_client):
        data_api_client.get_service.return_value = {'services': {
            'id': 1,
            'frameworkSlug': 'g-cloud-8',
            'supplierId': 2,
            'status': 'published'
        }}
        response = self.client.get('/admin/services/1')
        assert b'<input type="radio" name="service_status" id="service_status_disabled" value="removed"  />' in response.data  # noqa
        assert b'<input type="radio" name="service_status" id="service_status_private" value="private"  />' in response.data  # noqa
        assert b'<input type="radio" name="service_status" id="service_status_published" value="public" checked="checked" />' in response.data  # noqa

    def test_status_update_to_removed(self, data_api_client):
        data_api_client.get_service.return_value = {'services': {
            'frameworkSlug': 'g-cloud-7',
        }}
        response1 = self.client.post('/admin/services/status/1',
                                     data={'service_status': 'removed'})
        data_api_client.update_service_status.assert_called_with(
            '1', 'disabled', 'test@example.com')
        assert response1.status_code == 302
        assert response1.location == 'http://localhost/admin/services/1'
        response2 = self.client.get(response1.location)
        assert b'Service status has been updated to: Removed' in response2.data

    def test_status_update_to_private(self, data_api_client):
        data_api_client.get_service.return_value = {'services': {
            'frameworkSlug': 'g-cloud-8',
        }}
        response1 = self.client.post('/admin/services/status/1',
                                     data={'service_status': 'private'})
        data_api_client.update_service_status.assert_called_with(
            '1', 'enabled', 'test@example.com')
        assert response1.status_code == 302
        assert response1.location == 'http://localhost/admin/services/1'
        response2 = self.client.get(response1.location)
        assert b'Service status has been updated to: Private' in response2.data

    def test_status_update_to_published(self, data_api_client):
        data_api_client.get_service.return_value = {'services': {
            'frameworkSlug': 'digital-outcomes-and-specialists',
        }}
        response1 = self.client.post('/admin/services/status/1',
                                     data={'service_status': 'public'})
        data_api_client.update_service_status.assert_called_with(
            '1', 'published', 'test@example.com')
        assert response1.status_code == 302
        assert response1.location == 'http://localhost/admin/services/1'
        response2 = self.client.get(response1.location)
        assert b'Service status has been updated to: Public' in response2.data

    def test_bad_status_gives_error_message(self, data_api_client):
        data_api_client.get_service.return_value = {'services': {
            'frameworkSlug': 'g-cloud-7',
        }}
        response1 = self.client.post('/admin/services/status/1',
                                     data={'service_status': 'suspended'})
        assert response1.status_code == 302
        assert response1.location == 'http://localhost/admin/services/1'
        response2 = self.client.get(response1.location)
        assert b"Not a valid status: 'suspended'" in response2.data

    def test_services_with_missing_id(self, data_api_client):
        response = self.client.get('/admin/services')
        assert response.status_code == 404


class TestCompareServiceArchives(LoggedInApplicationTest):

    def setup_method(self, method):
        super(TestCompareServiceArchives, self).setup_method(method)
        self._services = {
            1: {'services': {
                'id': 1,
                'supplierId': 2,
                'updatedAt': '2014-12-10T10:55:25.00000Z',
                'serviceName': '<h1>Cloudy</h1> Cloud Service',
                'status': 'published',
                'serviceSummary': 'Something'
            }}
        }

        self._archived_services = {
            10: {'services': {
                'id': 1,
                'supplierId': 2,
                'updatedAt': '2014-12-01T10:55:25.00000Z',
                'serviceName': 'Cloud Service',
                'serviceSummary': 'Something'
            }},
            20: {'services': {
                'id': 1,
                'supplierId': 2,
                'updatedAt': '2014-12-02T10:55:25.00000Z',
                'serviceName': '<h1>Cloudy</h1> Cloud Service',
                'serviceSummary': 'Something'
            }},
            # Service id doesn't exist
            30: {'services': {
                'id': 2,
                'supplierId': 2,
                'updatedAt': '2014-12-03T10:55:25.00000Z'
            }},
            # Service id doesn't exist
            40: {'services': {
                'id': 2,
                'supplierId': 2,
                'updatedAt': '2014-12-04T10:55:25.00000Z'
            }},
            # missing the serviceSummary
            50: {'services': {
                'id': 1,
                'supplierId': 2,
                'updatedAt': '2014-12-03T10:55:25.00000Z',
                'serviceName': '<h1>Cloudy</h1> Cloud Service'
            }}
        }

        self._service_not_found = {
            'error': 'The requested URL was not found on the server.  If you '
                     'entered the URL manually please check your spelling and '
                     'try again.'
            }

    class _TestContent(object):
        def __init__(self):
            self.sections = [{
                'editable': True,
                'name': 'Description',
                'questions': [
                    {
                        'question': 'Service name',
                        'id': 'serviceName'
                    },
                    {
                        'question': 'Service summary',
                        'id': 'serviceSummary',
                    }
                ],
                'id': 'description'
            }]

    def _get_archived_service(self, *args):
        try:
            return self._archived_services[int(args[0])]
        except KeyError:
            return self._service_not_found

    def _get_service(self, *args):
        try:
            return self._services[int(args[0])]
        except KeyError:
            return self._service_not_found

    @mock.patch('app.main.views.services.data_api_client')
    def _get_archived_services_response(
            self,
            archived_service_id_1,
            archived_service_id_2,
            data_api_client
    ):
        data_api_client.get_archived_service.side_effect = \
            self._get_archived_service
        data_api_client.get_service.side_effect = self._get_service

        return self.client.get('/admin/services/compare/{}...{}'.format(
            archived_service_id_1, archived_service_id_2
        ))

    def test_cannot_get_nonexistent_archived_service(self):

        # Both archived services don't exist
        response = self._get_archived_services_response('1', '2')
        assert response.status_code == 404

        # First archived service doesn't exist
        response = self._get_archived_services_response('1', '20')
        assert response.status_code == 404

        # Second archived service doesn't exist
        response = self._get_archived_services_response('10', '2')
        assert response.status_code == 404

    def test_cannot_get_same_archived_service(self):

        response = self._get_archived_services_response('10', '10')
        assert response.status_code == 404

    def test_cannot_get_archived_services_in_non_chronological_order(self):

        response = self._get_archived_services_response('20', '10')
        assert response.status_code == 404

    def test_cannot_get_archived_services_for_nonexistent_service_ids(self):

        response = self._get_archived_services_response('30', '40')
        assert response.status_code == 404

    @mock.patch('app.main.views.services.content_loader')
    def test_can_get_archived_services_with_dates_and_diffs(self, content_loader):

        class TestBuilder(object):
            @staticmethod
            def filter(*args):
                return self._TestContent()

        content_loader.get_manifest.return_value = TestBuilder()
        response = self._get_archived_services_response('10', '20')

        # check title is there
        assert self.strip_all_whitespace(
            '<h1>&lt;h1&gt;Cloudy&lt;/h1&gt; Cloud Service</h1>'
        ) in self.strip_all_whitespace(response.get_data(as_text=True))

        # check dates are right
        assert self.strip_all_whitespace(
            'Monday 1 December 2014 at 10:55'
        ) in self.strip_all_whitespace(response.get_data(as_text=True))

        assert self.strip_all_whitespace(
            'Tuesday 2 December 2014 at 10:55'
        ) in self.strip_all_whitespace(response.get_data(as_text=True))

        # check lines are there
        assert self.strip_all_whitespace(
            '<td class=\'line-content unchanged\'>Cloud Service</td>'
        ) in self.strip_all_whitespace(response.get_data(as_text=True))

        assert self.strip_all_whitespace(
            '<td class=\'line-content addition\'><strong>&lt;h1&gt;Cloudy&lt;/h1&gt;</strong> Cloud Service</td>'
        ) in self.strip_all_whitespace(response.get_data(as_text=True))

        # check status is right
        assert self.strip_all_whitespace(
            '<input type="radio" name="service_status" id="service_status_published" value="public" checked=' +
            '"checked" />'
        ) in self.strip_all_whitespace(response.get_data(as_text=True))

    @mock.patch('app.main.views.services.content_loader')
    def test_can_get_archived_services_with_differing_keys(self, content_loader):

        class TestBuilder(object):
            @staticmethod
            def filter(*args):
                return self._TestContent()

        content_loader.get_manifest.return_value = TestBuilder()
        response = self._get_archived_services_response('10', '50')
        assert response.status_code == 200
