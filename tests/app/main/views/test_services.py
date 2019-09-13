from functools import partial
from io import BytesIO
from itertools import chain
from urllib.parse import urlsplit

import mock
import pytest
from dmapiclient import HTTPError
from dmapiclient.audit import AuditTypes
from dmutils import s3
from flask import Markup
from lxml import html

from dmtestutils.fixtures import valid_pdf_bytes

from ...helpers import LoggedInApplicationTest


class TestServiceFind(LoggedInApplicationTest):

    @pytest.mark.parametrize("role, expected_code", [
        ("admin", 302),
        ("admin-ccs-category", 302),
        ("admin-ccs-sourcing", 403),
        ("admin-framework-manager", 302),
        ("admin-manager", 403),
        ("admin-ccs-data-controller", 403),
    ])
    def test_service_find_is_only_accessible_to_specific_user_roles(self, role, expected_code):
        self.user_role = role
        response = self.client.get('/admin/services?service_id=314159265')
        actual_code = response.status_code
        assert actual_code == expected_code, "Unexpected response {} for role {}".format(actual_code, role)

    def test_service_find_redirects_to_view_for_valid_service_id(self):
        response = self.client.get('/admin/services?service_id=314159265')
        assert response.status_code == 302
        assert "/services/314159265" in response.location

    def test_service_find_returns_404_for_missing_service_id(self):
        response = self.client.get('/admin/services')
        assert response.status_code == 404


class TestServiceView(LoggedInApplicationTest):
    user_role = 'admin-ccs-category'

    find_audit_events_api_response = {'auditEvents': [
        {
            'createdAt': '2017-11-17T11:22:09.459945Z',
            'user': 'anne.admin@example.com',
            'type': 'update_service_status',
            'data': {
                'new_status': "disabled",
                'old_status': 'published',
                'serviceId': '314159265'
            }
        },
        {
            'createdAt': '2017-11-16T11:22:09.459945Z',
            'user': 'bob.admin@example.com',
            'type': 'update_service_status',
            'data': {
                'new_status': "published",
                'old_status': 'private',
                'serviceId': '314159265'
            }
        },
    ]}

    get_framework_api_response = {'frameworks': {'slug': 'g-cloud-8', 'status': 'live'}}

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.services.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    @pytest.mark.parametrize("fwk_status,expected_code", [
        ("coming", 404),
        ("open", 404),
        ("pending", 404),
        ("standstill", 404),
        ("live", 200),
        ("expired", 200),
    ])
    def test_view_service_only_accessible_for_live_and_expired_framework_services(self, fwk_status, expected_code):
        self.data_api_client.get_service.return_value = {'services': {
            'frameworkSlug': 'g-cloud-8',
            'serviceName': 'test',
            'supplierId': 1000,
            'lot': 'iaas',
            'id': "314159265",
            "status": "disabled",
        }}
        self.data_api_client.get_framework.return_value = {'frameworks': {'slug': 'g-cloud-8', 'status': fwk_status}}
        self.data_api_client.find_audit_events.return_value = self.find_audit_events_api_response
        response = self.client.get('/admin/services/314159265')
        actual_code = response.status_code

        assert actual_code == expected_code, "Unexpected response {} for {} framework".format(actual_code, fwk_status)

    def test_service_view_status_disabled(self):
        self.data_api_client.get_service.return_value = {'services': {
            'frameworkSlug': 'g-cloud-8',
            'serviceName': 'test',
            'supplierId': 1000,
            'lot': 'iaas',
            'id': "314159265",
            "status": "disabled",
        }}
        self.data_api_client.get_framework.return_value = self.get_framework_api_response
        self.data_api_client.find_audit_events.return_value = self.find_audit_events_api_response
        response = self.client.get('/admin/services/314159265')

        assert response.status_code == 200
        assert self.data_api_client.get_service.call_args_list == [
            (("314159265",), {}),
        ]
        assert self.data_api_client.find_audit_events.call_args_list == [
            mock.call(
                audit_type=AuditTypes.update_service_status,
                latest_first='true',
                object_id='314159265',
                object_type='services'
            )
        ]

        document = html.fromstring(response.get_data(as_text=True))
        assert document.xpath(
            "normalize-space(string(//td[@class='summary-item-field']//*[@class='service-id']))"
        ) == "314159265"

    def test_service_view_status_enabled(self):
        self.data_api_client.get_service.return_value = {'services': {
            'frameworkSlug': 'g-cloud-8',
            'serviceName': 'test',
            'supplierId': 1000,
            'lot': 'iaas',
            'id': "1412",
            "status": "enabled",
        }}
        self.data_api_client.get_framework.return_value = self.get_framework_api_response
        self.data_api_client.find_audit_events.return_value = self.find_audit_events_api_response
        response = self.client.get('/admin/services/1412')

        assert response.status_code == 200
        assert self.data_api_client.get_service.call_args_list == [
            (("1412",), {}),
        ]
        assert self.data_api_client.find_audit_events.call_args_list == [
            mock.call(
                audit_type=AuditTypes.update_service_status,
                latest_first='true',
                object_id='1412',
                object_type='services'
            )
        ]

        document = html.fromstring(response.get_data(as_text=True))
        assert document.xpath(
            "normalize-space(string(//td[@class='summary-item-field']//*[@class='service-id']))"
        ) == "1412"

    @pytest.mark.parametrize("role,expected_code", [
        ("admin", 200),
        ("admin-ccs-category", 200),
        ("admin-ccs-sourcing", 403),
        ("admin-framework-manager", 200),
        ("admin-manager", 403),
        ("admin-ccs-data-controller", 403),
    ])
    def test_view_service_is_only_accessible_to_specific_user_roles(self, role, expected_code):
        self.user_role = role
        self.data_api_client.get_service.return_value = {'services': {
            'frameworkSlug': 'g-cloud-8',
            'serviceName': 'test',
            'supplierId': 1000,
            'lot': 'iaas',
            'id': "314159265",
            "status": "disabled",
        }}
        self.data_api_client.get_framework.return_value = self.get_framework_api_response
        self.data_api_client.find_audit_events.return_value = self.find_audit_events_api_response
        response = self.client.get('/admin/services/314159265')
        actual_code = response.status_code
        assert actual_code == expected_code, "Unexpected response {} for role {}".format(actual_code, role)

    @pytest.mark.parametrize('service_status', ['disabled', 'enabled', 'published'])
    def test_service_view_with_data(self, service_status):
        service = {
            'frameworkSlug': 'g-cloud-8',
            'lot': 'iaas',
            'id': "151",
            "status": service_status,
            "serviceName": "Saint Leopold's",
            "serviceFeatures": [
                "Rabbitry and fowlrun",
                "Dovecote",
                "Botanical conservatory",
            ],
            "serviceBenefits": [
                "Mentioned in court and fashionable intelligence",
            ],
            "supplierId": 1000,
            "deviceAccessMethod": {
                "value": [
                    "Corporate/enterprise devices",
                    "Unknown devices",
                ],
                "assurance": "Independent validation of assertion",
            },
        }
        self.data_api_client.get_service.return_value = {'services': service}
        self.data_api_client.get_framework.return_value = self.get_framework_api_response
        self.data_api_client.find_audit_events.return_value = self.find_audit_events_api_response
        response = self.client.get('/admin/services/151')

        assert self.data_api_client.get_service.call_args_list == [
            (("151",), {}),
        ]
        assert response.status_code == 200

        document = html.fromstring(response.get_data(as_text=True))
        assert document.xpath(
            "normalize-space(string(//td[@class='summary-item-field']//*[@class='service-id']))"
        ) == "151"

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

    @pytest.mark.parametrize(
        ('service_status', 'called'),
        [
            ('disabled', True),
            ('enabled', True),
            ('published', False)
        ]
    )
    def test_find_audit_events_not_called_for_published(self, service_status, called):
        service = {
            'frameworkSlug': 'g-cloud-8',
            'lot': 'iaas',
            'id': "151",
            "status": service_status,
            "serviceName": "Saint Leopold's",
            "serviceFeatures": [
                "Rabbitry and fowlrun",
                "Dovecote",
                "Botanical conservatory",
            ],
            "serviceBenefits": [
                "Mentioned in court and fashionable intelligence",
            ],
            "supplierId": 1000,
            "deviceAccessMethod": {
                "value": [
                    "Corporate/enterprise devices",
                    "Unknown devices",
                ],
                "assurance": "Independent validation of assertion",
            },
        }
        self.data_api_client.get_service.return_value = {'services': service}
        self.data_api_client.get_framework.return_value = self.get_framework_api_response
        self.data_api_client.find_audit_events.return_value = self.find_audit_events_api_response
        response = self.client.get('/admin/services/151')

        assert response.status_code == 200
        assert self.data_api_client.find_audit_events.called is called

    @pytest.mark.parametrize('service_status', ['disabled', 'enabled'])
    def test_service_view_shows_info_banner_for_removed_and_private_services(self, service_status):
        self.data_api_client.get_service.return_value = {'services': {
            'frameworkSlug': 'g-cloud-8',
            'serviceName': 'test',
            'lot': 'iaas',
            'id': "314159265",
            'supplierId': 1000,
            "status": service_status,
        }}
        self.data_api_client.get_framework.return_value = self.get_framework_api_response
        self.data_api_client.find_audit_events.return_value = self.find_audit_events_api_response

        response = self.client.get('/admin/services/314159265')
        page_content = response.get_data(as_text=True)
        document = html.fromstring(response.get_data(as_text=True))

        assert len(document.xpath("//div[@class='banner-temporary-message-without-action']/h2")) == 1
        # Xpath doesn't handle non-breaking spaces well, so assert against page_content
        assert 'Removed by anne.admin@example.com on Friday&nbsp;17&nbsp;November&nbsp;2017.' in page_content
        assert self.data_api_client.find_audit_events.call_args_list == [
            mock.call(
                latest_first="true",
                object_id='314159265',
                object_type="services",
                audit_type=AuditTypes.update_service_status
            )
        ]

    @pytest.mark.parametrize('service_status', ['disabled', 'enabled'])
    def test_info_banner_contains_publish_link_for_ccs_category(self, service_status):
        self.data_api_client.get_service.return_value = {'services': {
            'frameworkSlug': 'g-cloud-8',
            'serviceName': 'test',
            'lot': 'iaas',
            'id': "314159265",
            'supplierId': 1000,
            "status": service_status,
        }}
        self.data_api_client.get_framework.return_value = self.get_framework_api_response
        self.data_api_client.find_audit_events.return_value = self.find_audit_events_api_response

        response = self.client.get('/admin/services/314159265')
        assert response.status_code == 200

        document = html.fromstring(response.get_data(as_text=True))
        expected_link_text = "Publish service"
        expected_href = '/admin/services/314159265?publish=True'
        expected_link = document.xpath('.//a[contains(@href,"{}")]'.format(expected_href))[0]

        assert expected_link.text == expected_link_text

    def test_service_view_does_not_show_info_banner_for_public_services(self):
        self.data_api_client.get_service.return_value = {'services': {
            'frameworkSlug': 'g-cloud-8',
            'serviceName': 'test',
            'lot': 'iaas',
            'id': "314159265",
            'supplierId': 1000,
            "status": 'published',
        }}
        self.data_api_client.get_framework.return_value = self.get_framework_api_response
        self.data_api_client.find_audit_events.return_value = self.find_audit_events_api_response

        response = self.client.get('/admin/services/314159265')

        document = html.fromstring(response.get_data(as_text=True))
        assert len(document.xpath("//div[@class='banner-temporary-message-without-action']/h2")) == 0
        assert self.data_api_client.find_audit_events.called is False

    @pytest.mark.parametrize('service_status', ['disabled', 'enabled', 'published'])
    def test_service_view_hides_information_banner_if_no_audit_events(self, service_status):
        self.data_api_client.get_service.return_value = {'services': {
            'frameworkSlug': 'g-cloud-8',
            'serviceName': 'test',
            'lot': 'iaas',
            'id': "314159265",
            'supplierId': 1000,
            "status": service_status,
        }}
        self.data_api_client.get_framework.return_value = self.get_framework_api_response
        self.data_api_client.find_audit_events.return_value = {'auditEvents': []}

        response = self.client.get('/admin/services/314159265')

        document = html.fromstring(response.get_data(as_text=True))
        assert len(document.xpath("//div[@class='banner-temporary-message-without-action']/h2")) == 0

    def test_redirect_with_flash_for_api_client_404(self):
        response = mock.Mock()
        response.status_code = 404
        self.data_api_client.get_service.side_effect = HTTPError(response)
        self.data_api_client.find_audit_events.return_value = self.find_audit_events_api_response

        response1 = self.client.get('/admin/services/1')
        assert response1.status_code == 302
        assert response1.location == 'http://localhost/admin/search'
        response2 = self.client.get(response1.location)
        assert b'Error trying to retrieve service with ID: 1' in response2.data

    def test_service_not_found_flash_message_injection(self):
        """
        Asserts that raw HTML in a bad service ID cannot be injected into a flash message.
        """
        # impl copied from test_redirect_with_flash_for_api_client_404
        api_response = mock.Mock()
        api_response.status_code = 404
        self.data_api_client.get_service.side_effect = HTTPError(api_response)
        self.data_api_client.find_audit_events.return_value = self.find_audit_events_api_response

        response1 = self.client.get('/admin/services/1%3Cimg%20src%3Da%20onerror%3Dalert%281%29%3E')
        response2 = self.client.get(response1.location)
        assert response2.status_code == 200

        html_response = response2.get_data(as_text=True)
        assert "1<img src=a onerror=alert(1)>" not in html_response
        assert "1&lt;img src=a onerror=alert(1)&gt;" in html_response

    def test_view_service_link_appears_for_gcloud_framework(self):
        self.data_api_client.get_service.return_value = {'services': {
            'lot': 'paas',
            'serviceName': 'test',
            'supplierId': 1000,
            'frameworkSlug': 'g-cloud-8',
            'frameworkFramework': 'g-cloud',
            'frameworkFamily': 'g-cloud',
            'id': "1",
            'status': 'published'
        }}
        self.data_api_client.get_framework.return_value = self.get_framework_api_response
        response = self.client.get('/admin/services/1')
        assert response.status_code == 200

        document = html.fromstring(response.get_data(as_text=True))
        expected_link_text = "View service"
        expected_href = '/g-cloud/services/1'
        expected_link = document.xpath('.//a[contains(@href,"{}")]'.format(expected_href))[0]

        assert expected_link.text == expected_link_text

    def test_view_service_link_does_not_appear_for_dos_framework(self):
        self.data_api_client.get_service.return_value = {'services': {
            'lot': 'paas',
            'serviceName': 'test',
            'supplierId': 1000,
            'frameworkSlug': 'digital-outcomes-and-specialists-2',
            'frameworkFramework': 'digital-outcomes-and-specialists',
            'frameworkFamily': 'digital-outcomes-and-specialists',
            'id': "1",
            'status': 'published'
        }}
        self.data_api_client.get_framework.return_value = self.get_framework_api_response
        response = self.client.get('/admin/services/1')
        assert response.status_code == 200

        document = html.fromstring(response.get_data(as_text=True))
        unexpected_href = '/g-cloud/services/1'

        assert not document.xpath('.//a[contains(@href,"{}")]'.format(unexpected_href))

    @pytest.mark.parametrize('url_suffix', ('', '?remove=True'))
    def test_remove_service_link_appears_for_correct_role_and_status(self, url_suffix):
        self.data_api_client.get_service.return_value = {'services': {
            'lot': 'paas',
            'serviceName': 'test',
            'supplierId': 1000,
            'frameworkSlug': 'digital-outcomes-and-specialists-2',
            'frameworkFramework': 'digital-outcomes-and-specialists',
            'frameworkFamily': 'digital-outcomes-and-specialists',
            'id': "1",
            'status': 'published'
        }}
        self.data_api_client.get_framework.return_value = self.get_framework_api_response
        response = self.client.get('/admin/services/1{}'.format(url_suffix))
        assert response.status_code == 200

        document = html.fromstring(response.get_data(as_text=True))
        expected_link_text = "Remove service"
        expected_href = '/admin/services/1?remove=True'
        expected_link = document.xpath('.//a[contains(@href,"{}")]'.format(expected_href))[0]

        assert expected_link.text == expected_link_text

    @pytest.mark.parametrize('action, service_status', [('publish', 'disabled'), ('remove', 'published')])
    @pytest.mark.parametrize('framework_status, links_shown', [('expired', 0), ('live', 1)])
    def test_remove_publish_service_links_only_appear_for_live_frameworks(
            self, framework_status, links_shown, action, service_status
    ):
        self.data_api_client.get_service.return_value = {'services': {
            'lot': 'paas',
            'serviceName': 'test',
            'supplierId': 1000,
            'frameworkSlug': 'digital-outcomes-and-specialists-2',
            'frameworkFramework': 'digital-outcomes-and-specialists',
            'frameworkFamily': 'digital-outcomes-and-specialists',
            'id': "1",
            'status': service_status
        }}
        framework = self.get_framework_api_response
        framework['frameworks']['status'] = framework_status
        self.data_api_client.get_framework.return_value = framework
        self.data_api_client.find_audit_events.return_value = self.find_audit_events_api_response

        response = self.client.get('/admin/services/1')
        assert response.status_code == 200

        document = html.fromstring(response.get_data(as_text=True))
        expected_href = '/admin/services/1?{}=True'.format(action)
        assert len(document.xpath('.//a[contains(@href,"{}")]'.format(expected_href))) == links_shown

    @pytest.mark.parametrize('user_role', ('admin-ccs-sourcing', 'admin-manager'))
    def test_no_access_for_certain_roles(self, user_role):
        self.user_role = user_role
        self.data_api_client.get_service.return_value = {'services': {
            'lot': 'paas',
            'serviceName': 'test',
            'supplierId': 1000,
            'frameworkSlug': 'digital-outcomes-and-specialists-2',
            'frameworkFramework': 'digital-outcomes-and-specialists',
            'frameworkFamily': 'digital-outcomes-and-specialists',
            'id': "1",
            'status': 'published'
        }}
        self.data_api_client.get_framework.return_value = self.get_framework_api_response
        response = self.client.get('/admin/services/1')
        assert response.status_code == 403

    @pytest.mark.parametrize('service_status', ['disabled', 'enabled'])
    def test_remove_service_does_not_appear_for_certain_statuses(self, service_status):
        self.data_api_client.get_service.return_value = {'services': {
            'lot': 'paas',
            'serviceName': 'test',
            'supplierId': 1000,
            'frameworkSlug': 'digital-outcomes-and-specialists-2',
            'frameworkFramework': 'digital-outcomes-and-specialists',
            'frameworkFamily': 'digital-outcomes-and-specialists',
            'id': "1",
            'status': service_status
        }}
        self.data_api_client.get_framework.return_value = self.get_framework_api_response
        self.data_api_client.find_audit_events.return_value = self.find_audit_events_api_response
        response = self.client.get('/admin/services/1')

        assert response.status_code == 200

        document = html.fromstring(response.get_data(as_text=True))
        unexpected_href = '/admin/services/1?remove=True'
        assert not document.xpath('.//a[contains(@href,"{}")]'.format(unexpected_href))

    def test_publish_service_does_not_appear_for_admin_role(self):
        self.user_role = 'admin'
        self.data_api_client.get_service.return_value = {'services': {
            'lot': 'paas',
            'serviceName': 'test',
            'supplierId': 1000,
            'frameworkSlug': 'digital-outcomes-and-specialists-2',
            'frameworkFramework': 'digital-outcomes-and-specialists',
            'frameworkFamily': 'digital-outcomes-and-specialists',
            'id': "1",
            'status': 'disabled'
        }}
        self.data_api_client.get_framework.return_value = self.get_framework_api_response
        self.data_api_client.find_audit_events.return_value = self.find_audit_events_api_response
        response = self.client.get('/admin/services/1')

        assert response.status_code == 200

        document = html.fromstring(response.get_data(as_text=True))
        unexpected_href = '/admin/services/1?publish=True'
        assert not document.xpath('.//a[contains(@href,"{}")]'.format(unexpected_href))

    def test_remove_service_does_not_appear_for_admin_role(self):
        self.user_role = 'admin'
        self.data_api_client.get_service.return_value = {'services': {
            'lot': 'paas',
            'serviceName': 'test',
            'supplierId': 1000,
            'frameworkSlug': 'digital-outcomes-and-specialists-2',
            'frameworkFramework': 'digital-outcomes-and-specialists',
            'frameworkFamily': 'digital-outcomes-and-specialists',
            'id': "1",
            'status': 'published'
        }}
        self.data_api_client.get_framework.return_value = self.get_framework_api_response
        self.data_api_client.find_audit_events.return_value = self.find_audit_events_api_response
        response = self.client.get('/admin/services/1')

        assert response.status_code == 200

        document = html.fromstring(response.get_data(as_text=True))
        unexpected_href = '/admin/services/1?remove=True'
        assert not document.xpath('.//a[contains(@href,"{}")]'.format(unexpected_href))

    def test_service_view_with_publish_param_shows_publish_banner(self):
        self.data_api_client.get_service.return_value = {'services': {
            'frameworkSlug': 'g-cloud-8',
            'serviceName': 'test',
            'lot': 'iaas',
            'id': "314159265",
            'supplierId': 1000,
            "status": 'disabled',
        }}
        self.data_api_client.get_framework.return_value = self.get_framework_api_response
        self.data_api_client.find_audit_events.return_value = self.find_audit_events_api_response

        response = self.client.get('/admin/services/314159265?publish=True')
        document = html.fromstring(response.get_data(as_text=True))
        banner_text = document.xpath("//div[@class='banner-destructive-with-action']/p")[0].text.strip()
        expected_text = "Are you sure you want to publish ‘test’?"

        assert banner_text == expected_text

    def test_service_view_with_remove_param_shows_remove_banner(self):
        self.data_api_client.get_service.return_value = {'services': {
            'frameworkSlug': 'g-cloud-8',
            'serviceName': 'test',
            'lot': 'iaas',
            'id': "314159265",
            'supplierId': 1000,
            "status": 'published',
        }}
        self.data_api_client.get_framework.return_value = self.get_framework_api_response
        self.data_api_client.find_audit_events.return_value = self.find_audit_events_api_response

        response = self.client.get('/admin/services/314159265?remove=True')
        document = html.fromstring(response.get_data(as_text=True))
        banner_text = document.xpath("//div[@class='banner-destructive-with-action']/p")[0].text.strip()
        expected_text = "Are you sure you want to remove ‘test’?"

        assert banner_text == expected_text


class TestServiceEdit(LoggedInApplicationTest):
    user_role = 'admin-ccs-category'

    get_framework_api_response = {'frameworks': {'slug': 'digital-outcomes-and-specialists-2', 'status': 'live'}}

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.services.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    @pytest.mark.parametrize("fwk_status,expected_code", [
        ("coming", 404),
        ("open", 404),
        ("pending", 404),
        ("standstill", 404),
        ("live", 200),
        ("expired", 200),
    ])
    def test_edit_service_only_accessible_for_live_and_expired_framework_services(self, fwk_status, expected_code):
        service = {
            "id": 123,
            "frameworkSlug": "digital-outcomes-and-specialists",
            "serviceName": "Larry O'Rourke's",
            "supplierId": 1000,
            "lot": "user-research-studios",
        }
        self.data_api_client.get_service.return_value = {'services': service}
        self.data_api_client.get_framework.return_value = {
            'frameworks': {'slug': 'digital-outcomes-and-specialists', 'status': fwk_status}
        }
        response = self.client.get('/admin/services/123/edit/description')
        actual_code = response.status_code

        assert actual_code == expected_code, "Unexpected response {} for {} framework".format(actual_code, fwk_status)

    @pytest.mark.parametrize("role,expected_code", [
        ("admin", 403),
        ("admin-ccs-category", 200),
        ("admin-ccs-sourcing", 403),
        ("admin-framework-manager", 403),
        ("admin-manager", 403),
        ("admin-ccs-data-controller", 403),
    ])
    def test_edit_service_is_only_accessible_to_specific_user_roles(self, role, expected_code):
        self.user_role = role
        service = {
            "id": 123,
            "frameworkSlug": "digital-outcomes-and-specialists",
            "serviceName": "Larry O'Rourke's",
            "supplierId": 1000,
            "lot": "user-research-studios",
        }
        self.data_api_client.get_service.return_value = {'services': service}
        self.data_api_client.get_framework.return_value = {
            'frameworks': {'slug': 'digital-outcomes-and-specialists', 'status': 'live'}
        }
        response = self.client.get('/admin/services/123/edit/description')
        actual_code = response.status_code
        assert actual_code == expected_code, "Unexpected response {} for role {}".format(actual_code, role)

    def test_edit_dos_service_title(self):
        service = {
            "id": 123,
            "frameworkSlug": "digital-outcomes-and-specialists",
            "serviceName": "Larry O'Rourke's",
            "supplierId": 1000,
            "lot": "user-research-studios",
        }
        self.data_api_client.get_service.return_value = {'services': service}
        self.data_api_client.get_framework.return_value = {
            'frameworks': {'slug': 'digital-outcomes-and-specialists', 'status': 'live'}
        }
        response = self.client.get('/admin/services/123/edit/description')
        document = html.fromstring(response.get_data(as_text=True))

        self.data_api_client.get_service.assert_called_with('123')

        assert response.status_code == 200
        assert document.xpath(
            "normalize-space(string(//input[@name='serviceName']/@value))"
        ) == service["serviceName"]
        assert document.xpath(
            "//div[contains(@class, 'govuk-breadcrumbs')]"
            "//a[@href='/admin/services/123'][normalize-space(string())=$t]",
            t=service["serviceName"],
        )

    def test_no_link_to_edit_dos2_service_essentials(self):
        service = {
            "id": 123,
            "frameworkSlug": "digital-outcomes-and-specialists-2",
            "serviceName": "Test",
            "supplierId": 1000,
            "lot": "digital-outcomes",
            'status': 'published'
        }
        self.data_api_client.get_service.return_value = {'services': service}
        self.data_api_client.get_framework.return_value = self.get_framework_api_response
        self.data_api_client.find_audit_events.return_value = {'auditEvents': []}

        response = self.client.get('/admin/services/123')
        assert response.status_code == 200

        document = html.fromstring(response.get_data(as_text=True))
        all_links_on_page = [i.values()[0] for i in document.xpath('(//body//a)')]
        assert '/admin/services/123/edit/service-essentials' not in all_links_on_page

    def test_add_link_for_empty_multiquestion(self):
        service = {
            "id": 123,
            "frameworkSlug": "digital-outcomes-and-specialists-2",
            "serviceName": "Test",
            "supplierId": 1000,
            "lot": "digital-outcomes",
            "performanceAnalysisAndData": '',
            'status': 'published'
        }

        self.data_api_client.get_service.return_value = {'services': service}
        self.data_api_client.get_framework.return_value = self.get_framework_api_response
        self.data_api_client.find_audit_events.return_value = {'auditEvents': []}

        response = self.client.get('/admin/services/123')
        assert response.status_code == 200

        document = html.fromstring(response.get_data(as_text=True))
        performance_analysis_and_data_link = "/admin/services/123/edit/team-capabilities/performance-analysis-and-data"
        performance_analysis_and_data_link_text = document.xpath(
            '//a[contains(@href, "{}")]//text()'.format(performance_analysis_and_data_link)
        )[0]
        assert performance_analysis_and_data_link_text == 'Add'

    def test_edit_link_for_populated_multiquestion(self):
        service = {
            "id": 123,
            "frameworkSlug": "digital-outcomes-and-specialists-2",
            "serviceName": "Test",
            "supplierId": 1000,
            "lot": "digital-outcomes",
            "performanceAnalysisTypes": 'some value',
            'status': 'published'
        }

        self.data_api_client.get_service.return_value = {'services': service}
        self.data_api_client.get_framework.return_value = self.get_framework_api_response
        self.data_api_client.find_audit_events.return_value = {'auditEvents': []}

        response = self.client.get('/admin/services/123')
        assert response.status_code == 200

        document = html.fromstring(response.get_data(as_text=True))
        performance_analysis_and_data_link = "/admin/services/123/edit/team-capabilities/performance-analysis-and-data"
        performance_analysis_and_data_link_text = document.xpath(
            '//a[contains(@href, "{}")]//text()'.format(performance_analysis_and_data_link)
        )[0]
        assert performance_analysis_and_data_link_text == 'Edit'

    def test_multiquestion_get_route(self):
        service = {
            "id": 123,
            "frameworkSlug": "digital-outcomes-and-specialists-2",
            "serviceName": "Test",
            "supplierId": 1000,
            "lot": "digital-specialists",
            "performanceAnalysisAndData": '',
        }

        self.data_api_client.get_service.return_value = {'services': service}
        self.data_api_client.get_framework.return_value = self.get_framework_api_response
        response = self.client.get('/admin/services/123/edit/individual-specialist-roles/business-analyst')

        assert response.status_code == 200

    def test_service_edit_documents_get_response(self):
        service = {
            "id": 321,
            'frameworkSlug': 'g-cloud-8',
            "serviceName": "Boylan the billsticker",
            "lot": "scs",
            "termsAndConditionsDocumentURL": "http://boylan.example.com/concert-tours",
        }
        self.data_api_client.get_service.return_value = {'services': service}
        self.data_api_client.get_framework.return_value = {'frameworks': {'slug': 'g-cloud-8', 'status': 'live'}}
        response = self.client.get('/admin/services/321/edit/documents')
        document = html.fromstring(response.get_data(as_text=True))

        self.data_api_client.get_service.assert_called_with('321')

        assert response.status_code == 200
        assert document.xpath("//input[@name='termsAndConditionsDocumentURL']")  # file inputs are complex, yeah?
        # ensure a field that data doesn't yet exist for is shown
        assert document.xpath("//input[@name='sfiaRateDocumentURL']")
        assert document.xpath(
            "//div[contains(@class, 'govuk-breadcrumbs')]"
            "//a[@href='/admin/services/321'][normalize-space(string())=$t]",
            t=service["serviceName"],
        )

    def test_service_edit_with_no_features_or_benefits(self):
        self.data_api_client.get_service.return_value = {'services': {
            'lot': 'saas',
            'frameworkSlug': 'g-cloud-8',
        }}
        self.data_api_client.get_framework.return_value = {'frameworks': {'slug': 'g-cloud-8', 'status': 'live'}}
        response = self.client.get(
            '/admin/services/234/edit/features-and-benefits')

        self.data_api_client.get_service.assert_called_with('234')

        assert response.status_code == 200
        assert 'id="input-serviceFeatures-0"class="text-box"value=""' in self.strip_all_whitespace(
            response.get_data(as_text=True)
        )

    def test_service_edit_with_one_service_feature(self):
        self.data_api_client.get_service.return_value = {'services': {
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
        self.data_api_client.get_framework.return_value = {'frameworks': {'slug': 'g-cloud-8', 'status': 'live'}}
        response = self.client.get(
            '/admin/services/1/edit/features-and-benefits'
        )
        assert response.status_code == 200
        stripped_page = self.strip_all_whitespace(response.get_data(as_text=True))
        assert 'id="input-serviceFeatures-0"class="text-box"value="bar"' in stripped_page
        assert 'id="input-serviceFeatures-1"class="text-box"value=""' in stripped_page

    def test_service_edit_assurance_questions(self):
        service = {
            'frameworkSlug': 'g-cloud-8',
            'lot': 'saas',
            'serviceAvailabilityPercentage': {
                "value": "31.415",
                "assurance": "Contractual commitment",
            },
        }
        self.data_api_client.get_service.return_value = {'services': service}
        self.data_api_client.get_framework.return_value = {'frameworks': {'slug': 'g-cloud-8', 'status': 'live'}}
        response = self.client.get('/admin/services/432/edit/asset-protection-and-resilience')
        document = html.fromstring(response.get_data(as_text=True))

        self.data_api_client.get_service.assert_called_with('432')

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

    def test_service_edit_with_no_section_returns_404(self):
        self.data_api_client.get_service.return_value = {'services': {
            'lot': 'saas',
            'frameworkSlug': 'g-cloud-8',
        }}
        self.data_api_client.get_framework.return_value = {'frameworks': {'slug': 'g-cloud-8', 'status': 'live'}}
        response = self.client.get(
            '/admin/services/234/edit/bad-section')

        self.data_api_client.get_service.assert_called_with('234')
        assert response.status_code == 404


class TestServiceUpdate(LoggedInApplicationTest):
    user_role = 'admin-ccs-category'

    get_framework_api_response = {'frameworks': {'slug': 'g-cloud-7', 'status': 'live'}}

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.services.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    @pytest.mark.parametrize("fwk_status,expected_code", [
        ("coming", 404),
        ("open", 404),
        ("pending", 404),
        ("standstill", 404),
        ("live", 302),
        ("expired", 302),
    ])
    def test_post_service_update_only_for_live_and_expired_framework_services(self, fwk_status, expected_code):
        self.data_api_client.get_service.return_value = {'services': {
            'id': 1,
            'supplierId': 2,
            'frameworkSlug': 'g-cloud-8',
            'lot': 'IaaS',
        }}
        self.data_api_client.get_framework.return_value = {'frameworks': {'slug': 'g-cloud-8', 'status': fwk_status}}
        response = self.client.post(
            '/admin/services/1/edit/features-and-benefits',
            data={
                'serviceFeatures': 'baz',
                'serviceBenefits': 'foo',
            }
        )
        actual_code = response.status_code

        assert actual_code == expected_code, "Unexpected response {} for {} framework".format(actual_code, fwk_status)

    @pytest.mark.parametrize("role,expected_code", [
        ("admin", 403),
        ("admin-ccs-category", 302),
        ("admin-ccs-sourcing", 403),
        ("admin-manager", 403),
        ("admin-ccs-data-controller", 403),
    ])
    def test_post_service_update_is_only_accessible_to_specific_user_roles(self, role, expected_code):
        self.user_role = role
        self.data_api_client.get_service.return_value = {'services': {
            'id': 1,
            'supplierId': 2,
            'frameworkSlug': 'g-cloud-8',
            'lot': 'IaaS',
        }}
        self.data_api_client.get_framework.return_value = {'frameworks': {'slug': 'g-cloud-8', 'status': 'live'}}
        response = self.client.post(
            '/admin/services/1/edit/features-and-benefits',
            data={
                'serviceFeatures': 'baz',
                'serviceBenefits': 'foo',
            }
        )
        actual_code = response.status_code
        assert actual_code == expected_code, "Unexpected response {} for role {}".format(actual_code, role)

    def test_service_update_documents_empty_post(self):
        self.data_api_client.get_service.return_value = {'services': {
            'id': 1,
            'supplierId': 2,
            'frameworkSlug': 'g-cloud-7',
            'lot': 'SCS',
            'serviceDefinitionDocumentURL': '',
            'termsAndConditionsDocumentURL': '',
            'sfiaRateDocumentURL': '',
            'pricingDocumentURL': '',
        }}
        self.data_api_client.get_framework.return_value = self.get_framework_api_response
        response = self.client.post(
            '/admin/services/1/edit/documents',
            data={}
        )

        self.data_api_client.get_service.assert_called_with('1')
        assert self.data_api_client.update_service.call_args_list == []

        assert response.status_code == 302
        assert urlsplit(response.location).path == "/admin/services/1"

    def test_service_update_documents(self):
        self.data_api_client.get_service.return_value = {'services': {
            'id': 1,
            'supplierId': 2,
            'frameworkSlug': 'g-cloud-7',
            'lot': 'SCS',
            'pricingDocumentURL': "http://assets/documents/1/2-pricing.pdf",
            'serviceDefinitionDocumentURL': "http://assets/documents/1/2-service-definition.pdf",
            'termsAndConditionsDocumentURL': "http://assets/documents/1/2-terms-and-conditions.pdf",
            'sfiaRateDocumentURL': None
        }}
        self.data_api_client.get_framework.return_value = self.get_framework_api_response
        response = self.client.post(
            '/admin/services/1/edit/documents',
            data={
                'serviceDefinitionDocumentURL': (BytesIO(), ''),
                'pricingDocumentURL': (BytesIO(valid_pdf_bytes), 'test.pdf'),
                'sfiaRateDocumentURL': (BytesIO(valid_pdf_bytes), 'test.pdf'),
                'termsAndConditionsDocumentURL': (BytesIO(b''), ''),
            }
        )

        self.data_api_client.get_service.assert_called_with('1')
        self.data_api_client.update_service.assert_called_with('1', {
            'pricingDocumentURL': 'https://assets.test.digitalmarketplace.service.gov.uk/g-cloud-7/documents/2/1-pricing-document-2015-01-01-1200.pdf',  # noqa
            'sfiaRateDocumentURL': 'https://assets.test.digitalmarketplace.service.gov.uk/g-cloud-7/documents/2/1-sfia-rate-card-2015-01-01-1200.pdf',  # noqa
        }, 'test@example.com', user_role='admin')

        assert response.status_code == 302

    def test_service_update_documents_with_validation_errors(self):
        self.data_api_client.get_service.return_value = {'services': {
            'id': 7654,
            'supplierId': 2,
            'frameworkSlug': 'g-cloud-7',
            'lot': 'SCS',
            'serviceDefinitionDocumentURL': "http://assets/documents/7654/2-service-definition.pdf",
            'pricingDocumentURL': "http://assets/documents/7654/2-pricing.pdf",
            'sfiaRateDocumentURL': None
        }}
        self.data_api_client.get_framework.return_value = self.get_framework_api_response
        response = self.client.post(
            '/admin/services/7654/edit/documents',
            data={
                'serviceDefinitionDocumentURL': (BytesIO(), ''),
                'pricingDocumentURL': (BytesIO(valid_pdf_bytes), 'test.pdf'),
                'sfiaRateDocumentURL': (BytesIO(valid_pdf_bytes), 'test.txt'),
                'termsAndConditionsDocumentURL': (BytesIO(), 'test.pdf'),
            }
        )
        document = html.fromstring(response.get_data(as_text=True))

        self.data_api_client.get_service.assert_called_with('7654')
        assert self.data_api_client.update_service.call_args_list == []
        assert response.status_code == 400

        assert document.xpath(
            "//*[contains(@class,'validation-message')][contains(normalize-space(string()), $t)]",
            t="Your document is not in an open format",
        )
        assert document.xpath(
            "//a[normalize-space(string())=$t]/@href",
            t="Return without saving",
        ) == ["/admin/services/7654"]

    def test_service_update_assurance_questions_when_API_returns_error(self):
        self.data_api_client.get_service.return_value = {'services': {
            'id': "7654",
            'supplierId': 2,
            'frameworkSlug': 'g-cloud-8',
            'lot': 'paas',
        }}
        self.data_api_client.get_framework.return_value = {'frameworks': {'slug': 'g-cloud-8', 'status': 'live'}}
        self.data_api_client.update_service.side_effect = HTTPError(
            None, {'dataProtectionWithinService': 'answer_required'}
        )
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
        self.data_api_client.get_service.assert_called_with('7654')
        assert self.data_api_client.update_service.call_args_list == [
            mock.call(
                '7654',
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
                'test@example.com', user_role='admin')
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

    def test_service_update_with_one_service_feature(self):
        self.data_api_client.get_service.return_value = {'services': {
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
        self.data_api_client.get_framework.return_value = {'frameworks': {'slug': 'g-cloud-8', 'status': 'live'}}
        response = self.client.post(
            '/admin/services/1/edit/features-and-benefits',
            data={
                'serviceFeatures': 'baz',
                'serviceBenefits': 'foo',
            }
        )

        assert self.data_api_client.update_service.call_args_list == [
            mock.call(
                '1',
                {'serviceFeatures': ['baz'], 'serviceBenefits': ['foo']},
                'test@example.com',
                user_role='admin'
            )]
        assert response.status_code == 302

    def test_service_update_multiquestion_post_route(self):
        service = {
            "id": 123,
            "frameworkSlug": "digital-outcomes-and-specialists-2",
            "serviceName": "Test",
            "lot": "digital-specialists",
            "businessAnalyst": '',
        }
        self.data_api_client.get_service.return_value = {'services': service}
        self.data_api_client.get_framework.return_value = {
            'frameworks': {'slug': 'digital-outcomes-and-specialists-2', 'status': 'live'}
        }
        data = {
            'businessAnalystLocations': ["London", "Offsite", "Scotland", "Wales"],
            'businessAnalystPriceMin': '100',
            'businessAnalystPriceMax': '150',
        }
        response = self.client.post(
            '/admin/services/123/edit/individual-specialist-roles/business-analyst',
            data=data
        )

        assert response.status_code == 302
        assert self.data_api_client.update_service.call_args_list == [
            mock.call('123', data, 'test@example.com', user_role='admin')
        ]

    def test_service_update_with_multiquestion_validation_error(self):
        self.data_api_client.get_service.return_value = {'services': {
            'id': 1,
            'supplierId': 2,
            'frameworkSlug': 'g-cloud-9',
            'lot': 'cloud-hosting',
            'serviceFeatures': [
                "bar",
            ],
            'serviceBenefits': [
                "foo",
            ],
        }}
        self.data_api_client.get_framework.return_value = {'frameworks': {'slug': 'g-cloud-9', 'status': 'live'}}
        mock_api_error = mock.Mock(status_code=400)
        mock_api_error.json.return_value = {
            "error": {"serviceBenefits": "under_10_words", "serviceFeatures": "under_10_words"}
        }
        self.data_api_client.update_service.side_effect = HTTPError(mock_api_error)

        response = self.client.post(
            '/admin/services/1/edit/service-features-and-benefits',
            data={
                'serviceFeatures': 'one 2 three 4 five 6 seven 8 nine 10 eleven',
                'serviceBenefits': '11 10 9 8 7 6 5 4 3 2 1',
            },
            follow_redirects=True
        )

        assert response.status_code == 400
        assert self.data_api_client.update_service.call_args_list == [
            mock.call(
                '1',
                {'serviceFeatures': ['one 2 three 4 five 6 seven 8 nine 10 eleven'],
                 'serviceBenefits': ['11 10 9 8 7 6 5 4 3 2 1']},
                'test@example.com', user_role='admin')
        ]

        document = html.fromstring(response.get_data(as_text=True))

        validation_banner_h2 = document.xpath("//h2[@class='validation-masthead-heading']//text()")[0].strip()
        assert validation_banner_h2 == "There was a problem with your answer to:"

        validation_banner_links = [
            (anchor.text_content(), anchor.get('href')) for anchor in
            document.xpath("//a[@class='validation-masthead-link']")
        ]
        assert sorted(validation_banner_links) == sorted([
            ("Service benefits", "#serviceBenefits"),
            ("Service features", "#serviceFeatures")
        ])

        validation_errors = [error.strip() for error in document.xpath("//span[@class='validation-message']//text()")]
        assert validation_errors == [
            "You can’t write more than 10 words for each feature.",
            "You can’t write more than 10 words for each benefit."
        ]

    def test_service_update_with_assurance_questions(self):
        self.data_api_client.get_service.return_value = {'services': {
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
        self.data_api_client.get_framework.return_value = {'frameworks': {'slug': 'g-cloud-8', 'status': 'live'}}
        response = self.client.post(
            '/admin/services/567/edit/external-interface-protection',
            data={
                'onboardingGuidance': 'false',
                'onboardingGuidance--assurance': "Service provider assertion",
                'interconnectionMethods': ["Private WAN"],
                'interconnectionMethods--assurance': "Service provider assertion",
            },
        )
        assert self.data_api_client.update_service.call_args_list == [
            mock.call(
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
                'test@example.com', user_role='admin')
        ]
        assert response.status_code == 302

    @mock.patch('app.main.views.services.upload_service_documents')
    def test_service_update_when_API_returns_error(self, upload_service_documents):
        assert isinstance(s3.S3, mock.Mock)

        self.data_api_client.get_service.return_value = {'services': {
            'id': 1,
            'supplierId': 2,
            'lot': 'SCS',
            'frameworkSlug': 'g-cloud-7',
            'pricingDocumentURL': "http://assets/documents/1/2-pricing.pdf",
            'sfiaRateDocumentURL': None
        }}
        self.data_api_client.get_framework.return_value = self.get_framework_api_response
        upload_service_documents.return_value = ({}, {})
        self.data_api_client.update_service.side_effect = HTTPError(None, {'sfiaRateDocumentURL': 'required'})

        response = self.client.post(
            '/admin/services/1/edit/documents',
            data={
                'pricingDocumentURL': (BytesIO(valid_pdf_bytes), 'test.pdf'),
                'sfiaRateDocumentURL': (BytesIO(valid_pdf_bytes), 'test.txt'),
                'termsAndConditionsDocumentURL': (BytesIO(), 'test.pdf'),
            }
        )
        assert 'There was a problem with the answer to this question' in response.get_data(as_text=True)

    def test_service_update_with_no_service_returns_404(self):
        self.data_api_client.get_service.return_value = None
        self.data_api_client.get_framework.return_value = self.get_framework_api_response
        response = self.client.post(
            '/admin/services/234/edit/documents',
            data={
                'pricingDocumentURL': (BytesIO(valid_pdf_bytes), 'test.pdf'),
                'sfiaRateDocumentURL': (BytesIO(valid_pdf_bytes), 'test.txt'),
                'termsAndConditionsDocumentURL': (BytesIO(), 'test.pdf'),
            }
        )

        self.data_api_client.get_service.assert_called_with('234')
        assert response.status_code == 404

    @pytest.mark.parametrize('framework_slug', ('g-cloud-7', 'digital-outcomes-and-specialists-2'))
    def test_service_update_with_no_section_returns_404(self, framework_slug):
        self.data_api_client.get_service.return_value = {'services': {
            'id': 1,
            'serviceName': 'test',
            'supplierId': 2,
            'lot': 'SCS',
            'frameworkSlug': framework_slug,
            'pricingDocumentURL': "http://assets/documents/1/2-pricing.pdf",
            'sfiaRateDocumentURL': None
        }}
        self.data_api_client.get_framework.return_value = {'frameworks': {'slug': framework_slug, 'status': 'live'}}
        response = self.client.post(
            '/admin/services/234/edit/bad-section',
            data={
                'pricingDocumentURL': (BytesIO(b"doc"), 'test.pdf'),
                'sfiaRateDocumentURL': (BytesIO(b"doc"), 'test.txt'),
                'termsAndConditionsDocumentURL': (BytesIO(), 'test.pdf'),
            }
        )

        self.data_api_client.get_service.assert_called_with('234')
        assert response.status_code == 404


class TestServiceStatusUpdate(LoggedInApplicationTest):
    user_role = 'admin-ccs-category'

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.services.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()

        self.data_api_client.find_audit_events.return_value = {'auditEvents': []}

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    @pytest.mark.parametrize("fwk_status,expected_code", [
        ("coming", 404),
        ("open", 404),
        ("pending", 404),
        ("standstill", 404),
        ("live", 302),
        ("expired", 302),
    ])
    def test_post_status_update_only_for_live_and_expired_framework_services(self, fwk_status, expected_code):
        self.data_api_client.get_service.return_value = {'services': {
            'frameworkSlug': 'g-cloud-9',
            'serviceName': 'bad service',
            'supplierId': 1000,
            'status': 'published',
        }}
        self.data_api_client.get_framework.return_value = {'frameworks': {'slug': 'g-cloud-9', 'status': fwk_status}}
        response = self.client.post('/admin/services/status/1',
                                    data={'service_status': 'removed'})
        actual_code = response.status_code

        assert actual_code == expected_code, "Unexpected response {} for {} framework".format(actual_code, fwk_status)

    @pytest.mark.parametrize("role,expected_code", [
        ("admin", 403),
        ("admin-ccs-category", 302),
        ("admin-ccs-sourcing", 403),
        ("admin-manager", 403),
        ("admin-ccs-data-controller", 403),
    ])
    def test_post_status_update_is_only_accessible_to_specific_user_roles(self, role, expected_code):
        self.user_role = role
        self.data_api_client.get_service.return_value = {'services': {
            'frameworkSlug': 'g-cloud-9',
            'serviceName': 'bad service',
            'supplierId': 1000,
            'status': 'published',
        }}
        self.data_api_client.get_framework.return_value = {'frameworks': {'slug': 'g-cloud-9', 'status': 'live'}}
        response = self.client.post('/admin/services/status/1',
                                    data={'service_status': 'removed'})
        actual_code = response.status_code

        assert actual_code == expected_code, "Unexpected response {} for role {}".format(actual_code, role)

    def test_status_update_to_removed(self):
        self.data_api_client.get_service.return_value = {'services': {
            'frameworkSlug': 'g-cloud-7',
            'serviceName': 'test',
            'supplierId': 1000,
            'status': 'published',
        }}
        self.data_api_client.get_framework.return_value = {'frameworks': {'slug': 'g-cloud-7', 'status': 'live'}}
        response = self.client.post('/admin/services/status/1', data={'service_status': 'removed'})
        self.data_api_client.update_service_status.assert_called_with('1', 'disabled', 'test@example.com')

        assert response.status_code == 302
        assert response.location == 'http://localhost/admin/services/1'
        self.assert_flashes('Service status has been updated to: removed')

    def test_status_update_to_service_with_no_name(self):
        self.data_api_client.get_service.return_value = {'services': {
            'frameworkName': 'G-cloud 7',
            'lotName': 'Cloud Hosting',
            'frameworkSlug': 'g-cloud-7',
            'supplierId': 1000,
            'status': 'published',
        }}
        self.data_api_client.get_framework.return_value = {'frameworks': {'slug': 'g-cloud-7', 'status': 'live'}}
        response = self.client.post('/admin/services/status/1', data={'service_status': 'public'})
        self.data_api_client.update_service_status.assert_called_with('1', 'published', 'test@example.com')

        assert response.status_code == 302
        assert response.location == 'http://localhost/admin/services/1'
        self.assert_flashes("You published ‘G-cloud 7 - Cloud Hosting’.")

    def test_cannot_update_status_to_private(self):
        self.data_api_client.get_service.return_value = {'services': {
            'frameworkSlug': 'g-cloud-8',
            'serviceName': 'test',
            'supplierId': 1000,
            'status': 'published',
        }}
        self.data_api_client.get_framework.return_value = {'frameworks': {'slug': 'g-cloud-8', 'status': 'live'}}
        response = self.client.post('/admin/services/status/1', data={'service_status': 'private'})

        assert not self.data_api_client.update_service_status.called
        assert response.status_code == 302
        assert response.location == 'http://localhost/admin/services/1'
        self.assert_flashes("Not a valid status: private", expected_category='error')

    def test_status_update_to_published(self):
        self.data_api_client.get_service.return_value = {'services': {
            'frameworkSlug': 'digital-outcomes-and-specialists',
            'serviceName': 'test',
            'supplierId': 1000,
            'status': 'enabled',
        }}

        self.data_api_client.get_framework.return_value = {
            'frameworks': {'slug': 'digital-outcomes-and-specialists', 'status': 'live'}
        }
        response = self.client.post('/admin/services/status/1', data={'service_status': 'public'})
        self.data_api_client.update_service_status.assert_called_with('1', 'published', 'test@example.com')

        assert response.status_code == 302
        assert response.location == 'http://localhost/admin/services/1'
        self.assert_flashes("You published ‘test’.")

    def test_bad_status_gives_error_message(self):
        self.data_api_client.get_service.return_value = {'services': {
            'frameworkSlug': 'g-cloud-7',
            'serviceName': 'test',
            'supplierId': 1000,
            'status': 'published',
        }}
        self.data_api_client.get_framework.return_value = {'frameworks': {'slug': 'g-cloud-7', 'status': 'live'}}
        response = self.client.post('/admin/services/status/1', data={'service_status': 'suspended'})

        assert response.status_code == 302
        assert response.location == 'http://localhost/admin/services/1'
        self.assert_flashes("Not a valid status: suspended", expected_category='error')

    def test_http_error_on_status_update_redirects_with_flash_error_message(self):
        self.data_api_client.get_service.return_value = {'services': {
            'frameworkSlug': 'g-cloud-7',
            'serviceName': 'test',
            'supplierId': 1000,
            'status': 'published',
        }}
        self.data_api_client.get_framework.return_value = {'frameworks': {'slug': 'g-cloud-7', 'status': 'live'}}
        self.data_api_client.update_service_status.side_effect = HTTPError(message='Something went wrong.')
        response = self.client.post('/admin/services/status/1', data={'service_status': 'public'})

        assert response.status_code == 302
        assert response.location == 'http://localhost/admin/services/1'
        self.assert_flashes(
            "Error trying to update status of service: Something went wrong.", expected_category='error'
        )

    def test_services_with_missing_id(self):
        response = self.client.get('/admin/services')

        assert response.status_code == 404


@mock.patch("app.main.views.services.html_diff_tables_from_sections_iter", autospec=True)
class TestServiceUpdates(LoggedInApplicationTest):

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.services.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    @pytest.mark.parametrize("role,expected_code", [
        ("admin", 403),
        ("admin-ccs-category", 200),
        ("admin-ccs-sourcing", 403),
        ("admin-manager", 403),
        ("admin-ccs-data-controller", 403),
    ])
    def test_view_service_updates_is_only_accessible_to_specific_user_roles(
            self, html_diff_tables_from_sections_iter, role, expected_code
    ):
        self.user_role = role
        self.data_api_client.get_service.return_value = self._mock_get_service_side_effect("published", "151")
        response = self.client.get('/admin/services/31415/updates')
        actual_code = response.status_code
        assert actual_code == expected_code, "Unexpected response {} for role {}".format(actual_code, role)

    def test_nonexistent_service(self, html_diff_tables_from_sections_iter):
        self.user_role = 'admin-ccs-category'
        self.data_api_client.get_service.return_value = None
        response = self.client.get('/admin/services/31415/updates')
        assert response.status_code == 404
        assert self.data_api_client.get_service.call_args_list == [(("31415",), {},)]

    @staticmethod
    def _mock_get_service_side_effect(status, service_id):
        return {"services": {
            "151": {
                "id": "151",
                "frameworkSlug": "g-cloud-9",
                "frameworkFamily": "g-cloud",
                "lot": "cloud-hosting",
                "status": status,
                "supplierId": 909090,
                "supplierName": "Barrington's",
                "serviceName": "Lemonflavoured soap",
            },
        }[service_id]}

    @staticmethod
    def _mock_get_archived_service_side_effect(old_versions_of_services, archived_service_id):
        return {"services": old_versions_of_services[archived_service_id]}

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
    def _mock_find_audit_events_side_effect(find_audit_events_api_response, implicit_page_len, **kwargs):
        if kwargs.get("page") or kwargs.get("page_len"):
            raise NotImplementedError

        links = {
            "self": "http://example.com/dummy",
        }
        if len(find_audit_events_api_response) > implicit_page_len:
            links["next"] = "http://example.com/dummy_next"
        if kwargs.get("latest_first") == "true":
            find_audit_events_api_response = find_audit_events_api_response[::-1]
        return {
            "auditEvents": find_audit_events_api_response[:implicit_page_len],
            "links": links,
        }

    _service_status_labels = {
        "disabled": "Removed",
        "enabled": "Private",
        "published": "Public",
    }

    expected_message_about_latest_edit_1 = "someone@example.com made 1 edit on Wednesday 3 February 2010."
    disabled_service_one_edit = (
        # find_audit_events api response:
        [
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
            }
        ],
        # old versions of edited services:
        {
            "789": {
                "frameworkSlug": "g-cloud-9",
                "lot": "cloud-hosting",
                "supplierId": 909090,
                "supplierName": "Barrington's",
                "serviceName": "Melonflavoured soap",
            },
        },
        # service status:
        "disabled",
        # expected message about the oldest unapproved edit:
        "Changed on Wednesday 3 February 2010 at 10:11am GMT",
        # number of audit events per page in API response + expected message about latest edit:
        ((5, expected_message_about_latest_edit_1,),),
    )

    expected_message_about_latest_edit_2 = "More than one user has edited this service. " \
        "The last user to edit this service was florrie@example.com on Sunday 22 March 2015."
    published_service_multiple_edits = (
        # find_audit_events api response:
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
        # old versions of edited services:
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
        # service status:
        "published",
        # expected message about the oldest unapproved edit:
        "Changed on Tuesday 3 February 2015 at 8:11pm GMT",
        # number of audit events per page in API response + expected message about latest edit:
        (
            (5, expected_message_about_latest_edit_2),
            (2, expected_message_about_latest_edit_2),
            (1, expected_message_about_latest_edit_2)
        )
    )

    expected_message_about_latest_edit_3 = "marion@example.com made 2 edits on Saturday 30 June 2012."
    enabled_service_multiple_edits_by_same_user = (
        # find_audit_events api response:
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
        # old versions of edited services:
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
        # service status:
        "enabled",
        # expected message about the oldest unapproved edit:
        "Changed on Saturday 30 June 2012 at 9:01pm BST",
        # number of audit events per page in API response + expected message about latest edit:
        (
            (5, expected_message_about_latest_edit_3),
            (2, expected_message_about_latest_edit_3),
            (1, expected_message_about_latest_edit_3)
        )
    )

    expected_message_about_latest_edit_4 = "More than one user has edited this service. " \
        "The last user to edit this service was private.carr@example.com on Saturday 17 December 2005."
    enabled_service_with_multiple_user_edits = (
        # find_audit_events api response:
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
        # old versions of edited services:
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
        # service status:
        "enabled",
        # expected message about the oldest unapproved edit:
        "Changed on Saturday 12 November 2005 at 3:01pm GMT",
        # number of audit events per page in API response + expected message about latest edit:
        (
            (5, expected_message_about_latest_edit_4),
            (3, expected_message_about_latest_edit_4),
            (2, expected_message_about_latest_edit_4)
        )
    )

    enabled_service_with_no_edits = (
        (),
        {},
        "enabled",
        None,
        ((5, "This service has no unapproved edits.",),)
    )

    @pytest.mark.parametrize(
        "find_audit_events_api_response,old_versions_of_services,service_status,"
        "expected_oldest_edit_info,find_audit_events_page_length",
        chain.from_iterable(
            (
                (fae_api_response, old_vers_of_services, service_status, expected_oldest_edit_info, fae_page_length)
                for fae_page_length, expected_message_about_latest_edit in variant_params
            )
            for fae_api_response, old_vers_of_services, service_status, expected_oldest_edit_info, variant_params in (
                disabled_service_one_edit,
                published_service_multiple_edits,
                enabled_service_multiple_edits_by_same_user,
                enabled_service_with_multiple_user_edits,
                enabled_service_with_no_edits,
            )
        )
    )
    @pytest.mark.parametrize("resultant_diff", (False, True))
    def test_unacknowledged_updates(
        self,
        html_diff_tables_from_sections_iter,
        find_audit_events_api_response,
        old_versions_of_services,
        service_status,
        expected_oldest_edit_info,
        find_audit_events_page_length,
        resultant_diff,
    ):
        self.data_api_client.get_service.side_effect = partial(self._mock_get_service_side_effect, service_status)
        self.data_api_client.find_audit_events.side_effect = partial(
            self._mock_find_audit_events_side_effect,
            find_audit_events_api_response,
            find_audit_events_page_length,
        )
        self.data_api_client.get_archived_service.side_effect = partial(
            self._mock_get_archived_service_side_effect,
            old_versions_of_services,
        )
        self.data_api_client.get_supplier.side_effect = self._mock_get_supplier_side_effect
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
            } for args, kwargs in self.data_api_client.find_audit_events.call_args_list
        )

        assert doc.xpath("normalize-space(string(//header//*[@class='context']))") == "Barrington's"
        assert doc.xpath("normalize-space(string(//header//h1))") == "Lemonflavoured soap"

        assert tuple(
            a.attrib["href"] for a in doc.xpath("//a[normalize-space(string())=$t]", t="View service")
        ) == ("/g-cloud/services/151",)

        assert len(doc.xpath(
            "//*[@class='dummy-diff-table']"
        )) == (1 if find_audit_events_api_response and resultant_diff else 0)
        assert len(doc.xpath(
            # an element that has the textual contents $reverted_text but doesn't have any children that have *exactly*
            # that text (this stops us getting multiple results for a single appearance of the text, because it includes
            # some of that element's parents - this should therefore select the bottom-most element that completely
            # contains the target text)
            "//*[normalize-space(string())=$reverted_text][not(.//*[normalize-space(string())=$reverted_text])]",
            reverted_text="All changes were reversed.",
        )) == (1 if find_audit_events_api_response and not resultant_diff else 0)

        if find_audit_events_api_response:
            assert html_diff_tables_from_sections_iter.call_args_list == [
                ((), {
                    "sections": mock.ANY,  # test separately later?
                    "revision_1":
                        old_versions_of_services[find_audit_events_api_response[0]["data"]["oldArchivedServiceId"]],
                    "revision_2": self._mock_get_service_side_effect(service_status, "151")["services"],
                    "table_preamble_template": "diff_table/_table_preamble.html",
                },),
            ]

            # in this case we want a strict assertion that *all* of the following are true about the ack_form
            ack_forms = doc.xpath(
                "//form[.//button[contains(text(), $ack_text)]]",
                ack_text="Approve edit{}".format("" if len(find_audit_events_api_response) == 1 else "s"),
            )
            assert len(ack_forms) == 1
            assert ack_forms[0].method == "POST"
            assert ack_forms[0].action == "/admin/services/151/updates/{}/approve".format(
                str(find_audit_events_api_response[-1]["id"])
            )
            assert sorted(ack_forms[0].form_values()) == [
                ("csrf_token", mock.ANY),
            ]

            assert bool(doc.xpath(
                "normalize-space(string(//h3[normalize-space(string())=$oldver_title]/ancestor::" +
                "*[contains(@class, 'column')][1]))",
                oldver_title="Previously approved version",
            ) == "Previously approved version " + expected_oldest_edit_info) == bool(resultant_diff)
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

    @pytest.mark.parametrize(
        "find_audit_events_api_response,old_versions_of_services,service_status,"
        "find_audit_events_page_length,expected_latest_edit_info",
        chain.from_iterable(
            (
                (
                    fae_api_response,
                    old_vers_of_services,
                    service_status,
                    find_audit_events_page_length,
                    expected_message_about_latest_edit,
                )
                for find_audit_events_page_length, expected_message_about_latest_edit in variant_params
            )
            for fae_api_response, old_vers_of_services, service_status, expected_oldest_edit_info, variant_params in (
                disabled_service_one_edit,
                published_service_multiple_edits,
                enabled_service_multiple_edits_by_same_user,
                enabled_service_with_multiple_user_edits,
                enabled_service_with_no_edits,
            )
        )
    )
    def test_service_edit_page_displays_last_user_to_edit_a_service(
        self,
        html_diff_tables_from_sections_iter,
        find_audit_events_api_response,
        old_versions_of_services,
        service_status,
        find_audit_events_page_length,
        expected_latest_edit_info,
    ):
        self.data_api_client.get_service.side_effect = partial(self._mock_get_service_side_effect, service_status)
        self.data_api_client.find_audit_events.side_effect = partial(
            self._mock_find_audit_events_side_effect,
            find_audit_events_api_response,
            find_audit_events_page_length,
        )
        self.data_api_client.get_archived_service.side_effect = partial(
            self._mock_get_archived_service_side_effect,
            old_versions_of_services,
        )
        self.data_api_client.get_supplier.side_effect = self._mock_get_supplier_side_effect

        self.user_role = "admin-ccs-category"
        response = self.client.get('/admin/services/151/updates')

        assert response.status_code == 200
        doc = html.fromstring(response.get_data(as_text=True))

        assert doc.xpath("//p[normalize-space(string())=$expected_text]", expected_text=expected_latest_edit_info)
