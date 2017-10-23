import pytest
from functools import partial
try:
    from urlparse import urlsplit
    from StringIO import StringIO
except ImportError:
    from urllib.parse import urlsplit
    from io import BytesIO as StringIO
from itertools import chain
import mock

from flask import Markup
from lxml import html
from six import text_type

from dmapiclient import HTTPError
from dmapiclient.audit import AuditTypes
from ...helpers import LoggedInApplicationTest
from dmutils import s3


class TestServiceFind(LoggedInApplicationTest):

    def test_service_find_redirects_to_view_for_valid_service_id(self):
        response = self.client.get('/admin/services?service_id=314159265')
        assert response.status_code == 302
        assert "/services/314159265" in response.location

    def test_service_find_returns_404_for_missing_service_id(self):
        response = self.client.get('/admin/services')
        assert response.status_code == 404


class TestServiceView(LoggedInApplicationTest):
    @mock.patch('app.main.views.services.data_api_client')
    def test_service_view_no_features_or_benefits_status_disabled(self, data_api_client):
        data_api_client.get_service.return_value = {'services': {
            'frameworkSlug': 'g-cloud-8',
            'lot': 'iaas',
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
            'lot': 'iaas',
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
    def test_service_view_with_data(self, data_api_client):
        service = {
            'frameworkSlug': 'g-cloud-8',
            'lot': 'iaas',
            'id': "151",
            "status": "published",
            "serviceName": "Saint Leopold's",
            "serviceFeatures": [
                "Rabbitry and fowlrun",
                "Dovecote",
                "Botanical conservatory",
            ],
            "serviceBenefits": [
                "Mentioned in court and fashionable intelligence",
            ],
            "deviceAccessMethod": {
                "value": [
                    "Corporate/enterprise devices",
                    "Unknown devices",
                ],
                "assurance": "Independent validation of assertion",
            },
        }
        data_api_client.get_service.return_value = {'services': service}
        response = self.client.get('/admin/services/151')

        assert data_api_client.get_service.call_args_list == [
            (("151",), {}),
        ]
        assert response.status_code == 200

        document = html.fromstring(response.get_data(as_text=True))
        assert document.xpath(
            "normalize-space(string(//td[@class='summary-item-field']//*[@class='service-id']))"
        ) == "151"

        assert frozenset(document.xpath("//input[@type='radio'][@name='service_status']/@value")) == frozenset((
            "removed",
            "private",
            "public",
        ))
        assert document.xpath("//input[@type='radio'][@name='service_status'][@checked]/@value") == ["public"]

        # check all serviceFeatures appear in an ul
        xpath_kwargs = {"a{}".format(i): term for i, term in enumerate(service["serviceFeatures"])}
        xpath_preds = "".join(
            "[./li[normalize-space(string())=$a{}]]".format(i) for i in range(len(service["serviceFeatures"]))
        )
        assert document.xpath(
            "//ul[count(./li)=$n_lis]{}".format(xpath_preds),
            n_lis=len(service["serviceFeatures"]),
            **xpath_kwargs
        )

        # ensure serviceBenefits is shown in a non-list-form
        assert document.xpath(
            "//*[@class='summary-item-field'][not(.//li)][normalize-space(string())=$s]",
            s=service["serviceBenefits"][0],
        )

        xpath_kwargs = {"a{}".format(i): term for i, term in enumerate(service["deviceAccessMethod"]["value"])}
        xpath_preds = "".join(
            "[./li[normalize-space(string())=$a{}]]".format(i)
            for i in range(len(service["deviceAccessMethod"]["value"]))
        )
        assert document.xpath(
            "//*[normalize-space(string())=$fullstr]/ul[count(./li)=$n_lis]{}".format(xpath_preds),
            fullstr=" ".join(chain(
                service["deviceAccessMethod"]["value"],
                ("Assured by", service["deviceAccessMethod"]["assurance"],),
            )),
            n_lis=len(service["deviceAccessMethod"]),
            **xpath_kwargs
        )

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
        service = {
            "id": 123,
            "frameworkSlug": "digital-outcomes-and-specialists",
            "serviceName": "Larry O'Rourke's",
            "lot": "user-research-studios",
        }
        data_api_client.get_service.return_value = {'services': service}
        response = self.client.get('/admin/services/123/edit/description')
        document = html.fromstring(response.get_data(as_text=True))

        data_api_client.get_service.assert_called_with('123')

        assert response.status_code == 200
        assert document.xpath(
            "normalize-space(string(//input[@name='serviceName']/@value))"
        ) == service["serviceName"]
        assert document.xpath(
            "//nav//a[@href='/admin/services/123'][normalize-space(string())=$t]",
            t=service["serviceName"],
        )

    @mock.patch('app.main.views.services.data_api_client')
    def test_service_edit_documents_get_response(self, data_api_client):
        service = {
            "id": 321,
            'frameworkSlug': 'g-cloud-8',
            "serviceName": "Boylan the billsticker",
            "lot": "scs",
            "termsAndConditionsDocumentURL": "http://boylan.example.com/concert-tours",
        }
        data_api_client.get_service.return_value = {'services': service}
        response = self.client.get('/admin/services/321/edit/documents')
        document = html.fromstring(response.get_data(as_text=True))

        data_api_client.get_service.assert_called_with('321')

        assert response.status_code == 200
        assert document.xpath("//input[@name='termsAndConditionsDocumentURL']")  # file inputs are complex, yeah?
        # ensure a field that data doesn't yet exist for is shown
        assert document.xpath("//input[@name='sfiaRateDocumentURL']")
        assert document.xpath(
            "//nav//a[@href='/admin/services/321'][normalize-space(string())=$t]",
            t=service["serviceName"],
        )

    @mock.patch('app.main.views.services.data_api_client')
    def test_service_edit_with_no_features_or_benefits(self, data_api_client):
        data_api_client.get_service.return_value = {'services': {
            'lot': 'saas',
            'frameworkSlug': 'g-cloud-8',
        }}
        response = self.client.get(
            '/admin/services/234/edit/features-and-benefits')

        data_api_client.get_service.assert_called_with('234')

        assert response.status_code == 200
        assert 'id="input-serviceFeatures-0"class="text-box"value=""' in self.strip_all_whitespace(
            response.get_data(as_text=True)
        )

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

    @mock.patch('app.main.views.services.data_api_client')
    def test_service_edit_assurance_questions(self, data_api_client):
        service = {
            'frameworkSlug': 'g-cloud-8',
            'lot': 'saas',
            'serviceAvailabilityPercentage': {
                "value": "31.415",
                "assurance": "Contractual commitment",
            },
        }
        data_api_client.get_service.return_value = {'services': service}
        response = self.client.get('/admin/services/432/edit/asset-protection-and-resilience')
        document = html.fromstring(response.get_data(as_text=True))

        data_api_client.get_service.assert_called_with('432')

        assert response.status_code == 200
        assert document.xpath(
            "//input[@name='serviceAvailabilityPercentage']/@value"
        ) == [service["serviceAvailabilityPercentage"]["value"]]
        assert document.xpath(
            "//input[@type='radio'][@name='serviceAvailabilityPercentage--assurance'][@checked]/@value"
        ) == ["Contractual commitment"]
        # ensure a field that data doesn't yet exist for is shown
        assert document.xpath("//input[@name='dataManagementLocations']")
        assert document.xpath("//input[@name='dataManagementLocations--assurance']")

    @mock.patch('app.main.views.services.data_api_client')
    def test_service_edit_with_no_section_returns_404(self, data_api_client):
        data_api_client.get_service.return_value = {'services': {
            'lot': 'saas',
            'frameworkSlug': 'g-cloud-8',
        }}
        response = self.client.get(
            '/admin/services/234/edit/bad-section')

        data_api_client.get_service.assert_called_with('234')
        assert response.status_code == 404


class TestServiceUpdate(LoggedInApplicationTest):
    @mock.patch('app.main.views.services.data_api_client')
    def test_service_update_documents_empty_post(self, data_api_client):
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
        assert data_api_client.update_service.call_args_list == []

        assert response.status_code == 302
        assert urlsplit(response.location).path == "/admin/services/1"

    @mock.patch('app.main.views.services.data_api_client')
    def test_service_update_documents(self, data_api_client):
        data_api_client.get_service.return_value = {'services': {
            'id': 1,
            'supplierId': 2,
            'frameworkSlug': 'g-cloud-7',
            'lot': 'SCS',
            'pricingDocumentURL': "http://assets/documents/1/2-pricing.pdf",
            'serviceDefinitionDocumentURL': "http://assets/documents/1/2-service-definition.pdf",
            'termsAndConditionsDocumentURL': "http://assets/documents/1/2-terms-and-conditions.pdf",
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
    def test_service_update_documents_with_validation_errors(
            self, data_api_client):
        data_api_client.get_service.return_value = {'services': {
            'id': 7654,
            'supplierId': 2,
            'frameworkSlug': 'g-cloud-7',
            'lot': 'SCS',
            'serviceDefinitionDocumentURL': "http://assets/documents/7654/2-service-definition.pdf",
            'pricingDocumentURL': "http://assets/documents/7654/2-pricing.pdf",
            'sfiaRateDocumentURL': None
        }}
        response = self.client.post(
            '/admin/services/7654/edit/documents',
            data={
                'serviceDefinitionDocumentURL': (StringIO(), ''),
                'pricingDocumentURL': (StringIO(b"doc"), 'test.pdf'),
                'sfiaRateDocumentURL': (StringIO(b"doc"), 'test.txt'),
                'termsAndConditionsDocumentURL': (StringIO(), 'test.pdf'),
            }
        )
        document = html.fromstring(response.get_data(as_text=True))

        data_api_client.get_service.assert_called_with('7654')
        assert data_api_client.update_service.call_args_list == []
        assert response.status_code == 400

        assert document.xpath(
            "//*[contains(@class,'validation-message')][contains(normalize-space(string()), $t)]",
            t="Your document is not in an open format",
        )
        assert document.xpath(
            "//a[normalize-space(string())=$t]/@href",
            t="Return without saving",
        ) == ["/admin/services/7654"]

    @mock.patch("app.main.views.services.data_api_client")
    def test_service_update_assurance_questions_when_API_returns_error(
            self, data_api_client):
        data_api_client.get_service.return_value = {'services': {
            'id': "7654",
            'supplierId': 2,
            'frameworkSlug': 'g-cloud-8',
            'lot': 'paas',
        }}
        data_api_client.update_service.side_effect = HTTPError(None, {'dataProtectionWithinService': 'answer_required'})
        posted_values = {
            "dataProtectionBetweenUserAndService": ["PSN assured service"],
            # dataProtectionWithinService deliberately omitted
            "dataProtectionBetweenServices": [
                "TLS (HTTPS or VPN) version 1.2 or later",
                "Legacy SSL or TLS (HTTPS or VPN)",
            ],
        }
        posted_assurances = {
            "dataProtectionBetweenUserAndService--assurance": "Independent testing of implementation",
            "dataProtectionWithinService--assurance": "CESG-assured components",
            "dataProtectionBetweenServices--assurance": "Service provider assertion",
        }

        response = self.client.post(
            "/admin/services/7654/edit/data-in-transit-protection",
            data=dict(posted_values, **posted_assurances),
        )
        document = html.fromstring(response.get_data(as_text=True))

        assert response.status_code == 400
        data_api_client.get_service.assert_called_with('7654')
        assert data_api_client.update_service.call_args_list == [
            (
                (
                    "7654",
                    {
                        "dataProtectionBetweenUserAndService": {
                            "value": posted_values["dataProtectionBetweenUserAndService"],
                            "assurance": posted_assurances["dataProtectionBetweenUserAndService--assurance"],
                        },
                        "dataProtectionWithinService": {
                            "assurance": posted_assurances["dataProtectionWithinService--assurance"],
                        },
                        "dataProtectionBetweenServices": {
                            "value": posted_values["dataProtectionBetweenServices"],
                            "assurance": posted_assurances["dataProtectionBetweenServices--assurance"],
                        },
                    },
                    "test@example.com",
                ),
                {},
            )
        ]

        for key, values in posted_values.items():
            assert sorted(document.xpath("//form//input[@type='checkbox'][@name=$n][@checked]/@value", n=key)) == \
                sorted(values)

        for key, value in posted_assurances.items():
            assert sorted(document.xpath("//form//input[@type='radio'][@name=$n][@checked]/@value", n=key)) == \
                [value]

        assert document.xpath(
            "//*[contains(@class,'validation-message')][contains(normalize-space(string()), $t)]",
            t="You need to answer this question",
        )
        assert document.xpath(
            "//a[normalize-space(string())=$t]/@href",
            t="Return without saving",
        ) == ["/admin/services/7654"]

    @mock.patch('app.main.views.services.data_api_client')
    def test_service_update_with_one_service_feature(self, data_api_client):
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
        response = self.client.post(
            '/admin/services/1/edit/features-and-benefits',
            data={
                'serviceFeatures': 'baz',
                'serviceBenefits': 'foo',
            }
        )
        assert data_api_client.update_service.call_args_list == [(
            (
                '1',
                {
                    'serviceFeatures': ['baz'],
                    'serviceBenefits': ['foo'],
                },
                'test@example.com',
            ),
            {},
        )]
        assert response.status_code == 302

    @mock.patch('app.main.views.services.data_api_client')
    def test_service_update_with_assurance_questions(self, data_api_client):
        data_api_client.get_service.return_value = {'services': {
            'id': 567,
            'supplierId': 987,
            'frameworkSlug': 'g-cloud-8',
            'lot': 'IaaS',
            'onboardingGuidance': {
                "value": False,
                "assurance": "Independent validation of assertion",
            },
            'interconnectionMethods': {
                "value": ["PSN assured service", "Private WAN"],
                "assurance": "Service provider assertion",
            },
        }}
        response = self.client.post(
            '/admin/services/567/edit/external-interface-protection',
            data={
                'onboardingGuidance': 'false',
                'onboardingGuidance--assurance': "Service provider assertion",
                'interconnectionMethods': ["Private WAN"],
                'interconnectionMethods--assurance': "Service provider assertion",
            },
        )
        assert data_api_client.update_service.call_args_list == [(
            (
                '567',
                {
                    'onboardingGuidance': {
                        "value": False,
                        "assurance": "Service provider assertion",
                    },
                    'interconnectionMethods': {
                        "value": ["Private WAN"],
                        "assurance": "Service provider assertion",
                    },
                },
                'test@example.com',
            ),
            {},
        )]
        assert response.status_code == 302

    @mock.patch('app.main.views.services.data_api_client')
    @mock.patch('app.main.views.services.upload_service_documents')
    def test_service_update_when_API_returns_error(self, upload_service_documents, data_api_client):
        assert isinstance(s3.S3, mock.Mock)

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
    def test_service_update_with_no_service_returns_404(self, data_api_client):
        data_api_client.get_service.return_value = None
        response = self.client.post(
            '/admin/services/234/edit/documents',
            data={
                'pricingDocumentURL': (StringIO(b"doc"), 'test.pdf'),
                'sfiaRateDocumentURL': (StringIO(b"doc"), 'test.txt'),
                'termsAndConditionsDocumentURL': (StringIO(), 'test.pdf'),
            }
        )

        data_api_client.get_service.assert_called_with('234')
        assert response.status_code == 404

    @mock.patch('app.main.views.services.data_api_client')
    def test_service_update_with_no_section_returns_404(self, data_api_client):
        data_api_client.get_service.return_value = {'services': {
            'id': 1,
            'supplierId': 2,
            'lot': 'SCS',
            'frameworkSlug': 'g-cloud-7',
            'pricingDocumentURL': "http://assets/documents/1/2-pricing.pdf",
            'sfiaRateDocumentURL': None
        }}
        response = self.client.post(
            '/admin/services/234/edit/bad-section',
            data={
                'pricingDocumentURL': (StringIO(b"doc"), 'test.pdf'),
                'sfiaRateDocumentURL': (StringIO(b"doc"), 'test.txt'),
                'termsAndConditionsDocumentURL': (StringIO(), 'test.pdf'),
            }
        )

        data_api_client.get_service.assert_called_with('234')
        assert response.status_code == 404


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


@mock.patch("app.main.views.services.html_diff_tables_from_sections_iter", autospec=True)
@mock.patch('app.main.views.services.data_api_client', autospec=True)
class TestServiceUpdates(LoggedInApplicationTest):
    def test_nonexistent_service(self, data_api_client, html_diff_tables_from_sections_iter):
        data_api_client.get_service.return_value = None
        response = self.client.get('/admin/services/31415/updates')
        assert response.status_code == 404
        assert data_api_client.get_service.call_args_list == [(("31415",), {},)]

    @staticmethod
    def _mock_get_service_side_effect(status, service_id):
        return {"services": {
            "151": {
                "id": "151",
                "frameworkSlug": "g-cloud-9",
                "lot": "cloud-hosting",
                "status": status,
                "supplierId": 909090,
                "supplierName": "Barrington's",
                "serviceName": "Lemonflavoured soap",
            },
        }[service_id]}

    @staticmethod
    def _mock_get_archived_service_side_effect(available_archived_services, archived_service_id):
        return {"services": available_archived_services[archived_service_id]}

    @staticmethod
    def _mock_get_supplier_side_effect(supplier_id):
        return {"suppliers": {
            909090: {
                "id": 909090,
                "name": "Barrington's",
                "contactInformation": [
                    {
                        "email": "sir.jonah.barrington@example.com",
                    },
                ],
            },
        }[supplier_id]}

    @staticmethod
    def _mock_find_audit_events_side_effect(fae_response_src, implicit_page_len, **kwargs):
        if kwargs.get("page") or kwargs.get("page_len"):
            raise NotImplementedError

        links = {
            "self": "http://example.com/dummy",
        }
        if len(fae_response_src) > implicit_page_len:
            links["next"] = "http://example.com/dummy_next"
        if kwargs.get("latest_first") == "true":
            fae_response_src = fae_response_src[::-1]
        return {
            "auditEvents": fae_response_src[:implicit_page_len],
            "links": links,
        }

    _service_status_labels = {
        "disabled": "Removed",
        "enabled": "Private",
        "published": "Public",
    }

    @pytest.mark.parametrize(
        "fae_response_src,avail_arch_svcs,svc_status,exp_oldver_ctxt_text,fae_page_len,exp_summ_text",
        chain.from_iterable(
            (
                (fae_r_s, avail_a_s, svc_s, exp_ov_c_t, fae_p_l, exp_s_t,)
                for fae_p_l, exp_s_t in variant_params
            )
            for fae_r_s, avail_a_s, svc_s, exp_ov_c_t, variant_params in (
                (
                    # fae_response_src (find_audit_events response source data)
                    (
                        {
                            "id": 567567,
                            "type": "update_service",
                            "acknowledged": False,
                            "data": {
                                "oldArchivedServiceId": "789",
                                "newArchivedServiceId": "678",
                            },
                            "createdAt": "2010-02-03T10:11:12.345Z",
                            "user": "someone@example.com",
                        },
                    ),
                    # avail_arch_svcs (available archived services)
                    {
                        "789": {
                            "frameworkSlug": "g-cloud-9",
                            "lot": "cloud-hosting",
                            "supplierId": 909090,
                            "supplierName": "Barrington's",
                            "serviceName": "Melonflavoured soap",
                        },
                    },
                    # svc_status (service status)
                    "disabled",
                    # exp_oldver_ctxt_text (expected oldversion title context text)
                    "Changed on Wednesday 3 February 2010 at 10:11am",
                    # sets of (fae_page_len, exp_summ_text) combinations to be flattened and joined against the above
                    # parameters^. this lets us reuse a long-winded description of the "universe" against many different
                    # implicit page_len values to test it with
                    (
                        (
                            # fae_page_len (find_audit_events implicit page_len)
                            5,
                            # exp_summ_text (expected summary text)
                            "1 unapproved edit by someone@example.com on Wednesday 3 February 2010.",
                        ),
                    ),
                ),
                (
                    (
                        {
                            "id": 1928374,
                            "type": "update_service",
                            "acknowledged": False,
                            "data": {
                                "oldArchivedServiceId": "111",
                                "newArchivedServiceId": "222",
                            },
                            "createdAt": "2015-02-03T20:11:12.345Z",
                            "user": "lynch@example.com",
                        },
                        {
                            "id": 293847,
                            "type": "update_service",
                            "acknowledged": False,
                            "data": {
                                "oldArchivedServiceId": "222",
                                "newArchivedServiceId": "333",
                            },
                            "createdAt": "2015-03-22T12:55:12.345Z",
                            "user": "lynch@example.com",
                        },
                        {
                            "id": 948576,
                            "type": "update_service",
                            "acknowledged": False,
                            "data": {
                                "oldArchivedServiceId": "333",
                                "newArchivedServiceId": "444",
                            },
                            "createdAt": "2015-03-22T12:57:12.345Z",
                            "user": "florrie@example.com",
                        },
                    ),
                    {
                        "111": {
                            "frameworkSlug": "g-cloud-9",
                            "lot": "cloud-hosting",
                            "supplierId": 909090,
                            "supplierName": "Mr Lambe from London",
                            "serviceName": "Lamb of London, who takest away the sins of our world.",
                            "somethingIrrelevant": "Soiled personal linen, wrong side up with care.",
                        },
                    },
                    "published",
                    "Changed on Tuesday 3 February 2015 at 8:11pm",
                    (
                        (
                            5,
                            (
                                "3 unapproved edits by 2 users between Tuesday 3 February 2015 and Sunday 22 "
                                "March 2015."
                            ),
                        ),
                        (
                            2,
                            (
                                "3 unapproved edits by 2 users between Tuesday 3 February 2015 and Sunday 22 "
                                "March 2015."
                            ),
                        ),
                        (
                            1,
                            (
                                "Multiple unapproved edits between Tuesday 3 February 2015 and Sunday 22 March "
                                "2015."
                            ),
                        ),
                    ),
                ),
                (
                    (
                        {
                            "id": 65432,
                            "type": "update_service",
                            "acknowledged": False,
                            "data": {
                                "oldArchivedServiceId": "4444",
                                "newArchivedServiceId": "5555",
                            },
                            "createdAt": "2012-06-30T20:01:12.345Z",
                            "user": "marion@example.com",
                        },
                        {
                            "id": 76543,
                            "type": "update_service",
                            "acknowledged": False,
                            "data": {
                                "oldArchivedServiceId": "5555",
                                "newArchivedServiceId": "6666",
                            },
                            "createdAt": "2012-06-30T22:55:12.345Z",
                            "user": "marion@example.com",
                        },
                    ),
                    {
                        "4444": {
                            "id": "151",
                            "frameworkSlug": "g-cloud-9",
                            "lot": "cloud-hosting",
                            "supplierId": 909090,
                            "supplierName": "Barrington's",
                            "serviceName": "Lemonflavoured soap",
                        },
                    },
                    "enabled",
                    "Changed on Saturday 30 June 2012 at 9:01pm",
                    (
                        (
                            5,
                            "2 unapproved edits by marion@example.com on Saturday 30 June 2012.",
                        ),
                        (
                            2,
                            "2 unapproved edits by marion@example.com on Saturday 30 June 2012.",
                        ),
                        (
                            1,
                            "Multiple unapproved edits on Saturday 30 June 2012.",
                        ),
                    ),
                ),
                (
                    (
                        {
                            "id": 556677,
                            "type": "update_service",
                            "acknowledged": False,
                            "data": {
                                "oldArchivedServiceId": "3535",
                                "newArchivedServiceId": "6767",
                            },
                            "createdAt": "2005-11-12T15:01:12.345Z",
                            "user": "private.carr@example.com",
                        },
                        {
                            "id": 668833,
                            "type": "update_service",
                            "acknowledged": False,
                            "data": {
                                "oldArchivedServiceId": "6767",
                                "newArchivedServiceId": "7373",
                            },
                            "createdAt": "2005-12-10T11:55:12.345Z",
                            "user": "private.carr@example.com",
                        },
                        {
                            "id": 449966,
                            "type": "update_service",
                            "acknowledged": False,
                            "data": {
                                "oldArchivedServiceId": "7373",
                                "newArchivedServiceId": "4747",
                            },
                            "createdAt": "2005-12-11T12:55:12.345Z",
                            "user": "cissy@example.com",
                        },
                        {
                            "id": 221188,
                            "type": "update_service",
                            "acknowledged": False,
                            "data": {
                                "oldArchivedServiceId": "4747",
                                "newArchivedServiceId": "9292",
                            },
                            "createdAt": "2005-12-17T09:22:12.345Z",
                            "user": "private.carr@example.com",
                        },
                    ),
                    {
                        "3535": {
                            "id": "151",
                            "frameworkSlug": "g-cloud-9",
                            "lot": "cloud-hosting",
                            "supplierId": 909090,
                            "supplierName": "Barrington's",
                            "serviceName": "Lemonflavoured soup",
                        },
                    },
                    "enabled",
                    "Changed on Saturday 12 November 2005 at 3:01pm",
                    (
                        (
                            5,
                            (
                                "4 unapproved edits by 2 users between Saturday 12 November 2005 and Saturday 17 "
                                "December 2005."
                            ),
                        ),
                        (
                            3,
                            (
                                "4 unapproved edits by 2 users between Saturday 12 November 2005 and Saturday 17 "
                                "December 2005."
                            ),
                        ),
                        (
                            2,
                            (
                                "Multiple unapproved edits between Saturday 12 November 2005 and Saturday 17 "
                                "December 2005."
                            ),
                        ),
                    ),
                ),
                (
                    (),
                    {},
                    "enabled",
                    None,
                    (
                        (
                            5,
                            "0 unapproved edits.",
                        ),
                    ),
                ),
            )
        )
    )
    @pytest.mark.parametrize("resultant_diff", (False, True))
    def test_unacknowledged_updates(
        self,
        data_api_client,
        html_diff_tables_from_sections_iter,
        fae_response_src,
        avail_arch_svcs,
        svc_status,
        exp_oldver_ctxt_text,
        fae_page_len,
        exp_summ_text,
        resultant_diff,
    ):
        data_api_client.get_service.side_effect = partial(self._mock_get_service_side_effect, svc_status)
        data_api_client.find_audit_events.side_effect = partial(
            self._mock_find_audit_events_side_effect,
            fae_response_src,
            fae_page_len,
        )
        data_api_client.get_archived_service.side_effect = partial(
            self._mock_get_archived_service_side_effect,
            avail_arch_svcs,
        )
        data_api_client.get_supplier.side_effect = self._mock_get_supplier_side_effect
        html_diff_tables_from_sections_iter.side_effect = lambda *a, **ka: iter((
            ("dummy_section", "dummy_question", Markup("<div class='dummy-diff-table'>dummy</div>")),
        ) if resultant_diff else ())

        self.user_role = "admin-ccs-category"
        response = self.client.get('/admin/services/151/updates')

        assert response.status_code == 200
        doc = html.fromstring(response.get_data(as_text=True))

        assert all(
            kwargs == {
                "object_id": "151",
                "object_type": "services",
                "audit_type": AuditTypes.update_service,
                "acknowledged": "false",
                "latest_first": mock.ANY,
            } for args, kwargs in data_api_client.find_audit_events.call_args_list
        )

        assert doc.xpath("normalize-space(string(//header//*[@class='context']))") == "Barrington's"
        assert doc.xpath("normalize-space(string(//header//h1))") == "Lemonflavoured soap"

        assert doc.xpath("//p[normalize-space(string())=$expected_text]", expected_text=exp_summ_text)

        assert len(doc.xpath("//*[@class='dummy-diff-table']")) == (1 if fae_response_src and resultant_diff else 0)
        assert len(doc.xpath(
            # an element that has the textual contents $reverted_text but doesn't have any children that have *exactly*
            # that text (this stops us getting multiple results for a single appearance of the text, because it includes
            # some of that element's parents - this should therefore select the bottom-most element that completely
            # contains the target text)
            "//*[normalize-space(string())=$reverted_text][not(.//*[normalize-space(string())=$reverted_text])]",
            reverted_text="All changes were reversed.",
        )) == (1 if fae_response_src and not resultant_diff else 0)

        if fae_response_src:
            assert html_diff_tables_from_sections_iter.call_args_list == [
                ((), {
                    "sections": mock.ANY,  # test separately later?
                    "revision_1": avail_arch_svcs[fae_response_src[0]["data"]["oldArchivedServiceId"]],
                    "revision_2": self._mock_get_service_side_effect(svc_status, "151")["services"],
                    "table_preamble_template": "diff_table/_table_preamble.html",
                },),
            ]

            # in this case we want a strict assertion that *all* of the following are true about the ack_form
            ack_forms = doc.xpath(
                "//form[.//input[@type='submit' and @value=$ack_text]]",
                ack_text="Approve edit{}".format("" if len(fae_response_src) == 1 else "s"),
            )
            assert len(ack_forms) == 1
            assert ack_forms[0].method == "POST"
            assert ack_forms[0].action == "/admin/services/151/updates/{}/approve".format(
                text_type(fae_response_src[-1]["id"])
            )
            assert sorted(ack_forms[0].form_values()) == [
                ("csrf_token", mock.ANY),
            ]

            assert bool(doc.xpath(
                "normalize-space(string(//h3[normalize-space(string())=$oldver_title]/ancestor::" +
                "*[contains(@class, 'column')][1]))",
                oldver_title="Previously approved version",
            ) == "Previously approved version " + exp_oldver_ctxt_text) == bool(resultant_diff)
        else:
            # in this case we want a loose assertion that nothing exists that has anything like any of these properties
            assert not doc.xpath(
                "//form[.//button[@type='submit'][contains(normalize-space(string()), $ack_text)]]",
                ack_text="Approve edit",
            )
            assert not any(form.action.endswith("approve") for form in doc.xpath("//form"))

            assert not doc.xpath(
                "//h3[normalize-space(string())=$oldver_title]",
                oldver_title="Previously approved version",
            )

        assert doc.xpath(
            "//*[.//h4[normalize-space(string())=$title]][normalize-space(string())=$full]" +
            "[.//a[@href=$mailto][normalize-space(string())=$email]]",
            title="Contact supplier:",
            full="Contact supplier: sir.jonah.barrington@example.com",
            mailto="mailto:sir.jonah.barrington@example.com",
            email="sir.jonah.barrington@example.com",
        )
