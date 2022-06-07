# -*- coding: utf-8 -*-
import mock
import pytest
from lxml import html

from ...helpers import LoggedInApplicationTest


class TestServiceUpdates(LoggedInApplicationTest):
    user_role = 'admin-ccs-category'

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.service_updates.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    @pytest.mark.parametrize("role,expected_code", [
        ("admin", 403),
        ("admin-ccs-category", 200),
        ("admin-ccs-sourcing", 403),
        ("admin-manager", 403),
    ])
    def test_view_service_updates_only_for_allowed_user_roles(self, role, expected_code):
        self.user_role = role
        response = self.client.get('/admin/services/updates/unapproved')
        actual_code = response.status_code
        assert actual_code == expected_code, "Unexpected response {} for role {}".format(actual_code, role)

    @pytest.mark.parametrize('audit_events,expected_table_contents,expected_count', (
        (
            (
                ('2012-07-15T18:03:43.061077Z', '1123456789012351', u'Company name', '240697', '240680'),
                ('2016-03-05T10:42:16.061077Z', '1123456789012348', u'Testing Ltd', '240699', '240682'),
                ('2017-04-25T14:43:46.061077Z', '597637931594387', u'Making £ Inc', '240701', '240684'),
            ),
            (
                ('Company name', '1123456789012351', 'Sunday 15 July 2012 at 18:03:43', '/admin/services/1123456789012351/updates'),  # noqa
                ('Testing Ltd', '1123456789012348', 'Saturday 5 March 2016 at 10:42:16', '/admin/services/1123456789012348/updates'),  # noqa
                ('Making £ Inc', '597637931594387', 'Tuesday 25 April 2017 at 14:43:46', '/admin/services/597637931594387/updates'),  # noqa
            ),
            '3 edited services',
        ),
        (
            (
                ('2012-07-15T18:03:43.061077Z', '597637931590002', 'Company name', '240697', '240680'),
                ('2016-03-05T10:42:16.061077Z', '597637931590001', 'Ideal Health', '240699', '240682'),
            ),
            (
                ('Company name', '597637931590002', 'Sunday 15 July 2012 at 18:03:43', '/admin/services/597637931590002/updates'),  # noqa
                ('Ideal Health', '597637931590001', 'Saturday 5 March 2016 at 10:42:16', '/admin/services/597637931590001/updates'),  # noqa
            ),
            '2 edited services',
        ),
        (
            (),
            (),
            '0 edited services',
        ),
        (
            (
                ('2012-07-15T18:03:43.061077Z', '597637931590002', 'Company name', '240697', '240680'),
            ),
            (
                ('Company name', '597637931590002', 'Sunday 15 July 2012 at 18:03:43', '/admin/services/597637931590002/updates'),  # noqa
            ),
            '1 edited service',
        ),
    ))
    def test_should_show_unacknowledged_services(self, audit_events, expected_table_contents, expected_count):
        self.data_api_client.find_audit_events.return_value = {
            "auditEvents": [
                {
                    "data": {
                        "oldArchivedServiceId": old_archived_service_id,
                        "newArchivedServiceId": new_archived_service_id,
                        "serviceId": service_id,
                        "supplierName": supplier_name,
                    },
                    "createdAt": date_string
                } for (
                    date_string, service_id, supplier_name, old_archived_service_id, new_archived_service_id
                ) in audit_events
            ],
            "links": {},
        }

        response = self.client.get('/admin/services/updates/unapproved')

        assert response.status_code == 200
        document = html.fromstring(response.get_data(as_text=True))

        assert tuple(
            tuple(
                td.xpath('normalize-space(string())') for td in tr.xpath('./td')[:-1]
            ) + (tr.xpath('./td[last()]//a/@href')[0],)
            for tr in document.xpath('//table[@class="summary-item-body"]/tbody/tr')
        ) == expected_table_contents

        assert len(document.cssselect(f'p.govuk-body.search-summary:contains("{expected_count}")')) == 1

        if audit_events != ():
            assert tuple(
                tuple(th.xpath('normalize-space(string())') for th in tr.xpath('./th'))
                for tr in document.xpath('//table[@class="summary-item-body"]/thead/tr')
            ) == (('Supplier', 'Service ID', 'Edited', 'Changes'),)

    def test_acknowledge_audit_event_happy_path(self):
        audit_event = {
            'auditEvents': {
                'acknowledged': False,
                'links': {
                    'self': 'http://localhost:5000/services/updates/unapproved'
                },
                'data': {
                    'serviceName': 'new name',
                    'supplierId': 93518,
                    'supplierName': 'Clouded Networks',
                    'serviceId': '321',
                },
                'user': 'joeblogs',
                'type': 'update_service',
                'id': 123,
                'createdAt': '2015-06-17T08:49:22.999Z'
            },
            'links': {}
        }

        self.data_api_client.get_audit_event.side_effect = lambda audit_event_id: {123: audit_event}[audit_event_id]
        response = self.client.post('/admin/services/321/updates/123/approve')
        assert response.status_code == 302
        self.assert_flashes("The changes to service 321 were approved.")
        assert response.location == 'http://localhost/admin/services/updates/unapproved'

        self.data_api_client.acknowledge_service_update_including_previous.assert_called_with(
            u'321',
            123,
            'test@example.com'
        )

    def test_should_404_wrong_service_id(self):
        response = self.client.post('/admin/services/123/updates/321/approve')
        assert response.status_code == 404

    @pytest.mark.parametrize("role_not_allowed", ["admin", "admin-ccs-sourcing", "admin-manager"])
    def test_post_should_403_forbidden_user_roles(self, role_not_allowed):
        self.user_role = role_not_allowed
        response = self.client.post('/admin/services/123/updates/321/approve')
        assert response.status_code == 403

    def test_should_410_already_acknowledged_event(self):
        audit_event = {
            'auditEvents': {
                'acknowledged': True,
                'links': {
                    'self': 'http://localhost:5000/audit-events'
                },
                'data': {
                    'serviceName': 'new name',
                    'supplierId': 93518,
                    'supplierName': 'Clouded Networks',
                    'serviceId': '321',
                },
                'user': 'joeblogs',
                'type': 'update_service',
                'id': 123,
                'createdAt': '2015-06-17T08:49:22.999Z'
            },
            'links': {}
        }

        self.data_api_client.get_audit_event.side_effect = lambda audit_event_id: {123: audit_event}[audit_event_id]
        response = self.client.post('/admin/services/321/updates/123/approve')
        assert response.status_code == 410

    def test_should_404_wrong_audit_event_type(self):
        audit_event = {
            'auditEvents': {
                'acknowledged': False,
                'links': {
                    'self': 'http://localhost:5000/audit-events'
                },
                'data': {
                    'serviceName': 'new name',
                    'supplierId': 93518,
                    'supplierName': 'Clouded Networks',
                    'serviceId': '321',
                },
                'user': 'joeblogs',
                'type': 'not_the_right_type',
                'id': 123,
                'createdAt': '2015-06-17T08:49:22.999Z'
            },
            'links': {}
        }

        self.data_api_client.get_audit_event.side_effect = lambda audit_event_id: {123: audit_event}[audit_event_id]
        response = self.client.post('/admin/services/321/updates/123/approve')
        assert response.status_code == 404

    @mock.patch('app.main.views.service_updates.s3')
    @mock.patch('app.main.views.service_updates.get_signed_url')
    def test_report_download_redirects_to_s3(self, get_signed_url, s3):
        get_signed_url.return_value = 'http://asseturl/path/to/csv?querystring'
        self.app.config['DM_ASSETS_URL'] = 'http://example.com'

        response = self.client.get('/admin/services/updates/approved/2022-06')
        assert response.status_code == 302

        assert get_signed_url.call_args_list == [
            mock.call(
                s3.S3.return_value,
                "common/reports/approved-service-edits-2022-06.csv",
                'http://example.com'
            ),
        ]
