# -*- coding: utf-8 -*-
import mock
import pytest
from lxml import html

from tests.app.main.helpers.flash_tester import assert_flashes
from ...helpers import LoggedInApplicationTest


@mock.patch('app.main.views.service_updates.data_api_client', autospec=True)
class TestServiceUpdates(LoggedInApplicationTest):
    user_role = 'admin-ccs-category'

    @pytest.mark.parametrize('audit_events,expected_table_contents,expected_count', (
        (
            (
                ('2012-07-15T18:03:43.061077Z', '1123456789012351', u'Company name', '240697', '240680'),
                ('2016-03-05T10:42:16.061077Z', '1123456789012348', u'Testing Ltd', '240699', '240682'),
                ('2017-04-25T14:43:46.061077Z', '597637931594387', u'Making £ Inc', '240701', '240684'),
            ),
            (
                ('Company name', '1123456789012351', '15 July at 19:03:43', '/admin/services/1123456789012351/updates'),
                (u'Testing Ltd', '1123456789012348', '5 March at 10:42:16', '/admin/services/1123456789012348/updates'),
                (u'Making £ Inc', '597637931594387', '25 April at 15:43:46', '/admin/services/597637931594387/updates'),
            ),
            '3 edited services',
        ),
        (
            (
                ('2012-07-15T18:03:43.061077Z', '597637931590002', 'Company name', '240697', '240680'),
                ('2016-03-05T10:42:16.061077Z', '597637931590001', 'Ideal Health', '240699', '240682'),
            ),
            (
                ('Company name', '597637931590002', '15 July at 19:03:43', '/admin/services/597637931590002/updates'),
                ('Ideal Health', '597637931590001', '5 March at 10:42:16', '/admin/services/597637931590001/updates'),
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
                ('Company name', '597637931590002', '15 July at 19:03:43', '/admin/services/597637931590002/updates'),
            ),
            '1 edited service',
        ),
    ))
    def test_should_show_unacknowledged_services(
            self, data_api_client, audit_events, expected_table_contents, expected_count):
        data_api_client.find_audit_events.return_value = {
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

        assert document.xpath('normalize-space(string(//*[@class="search-summary"]))') == expected_count

        if audit_events != ():
            assert tuple(
                tuple(th.xpath('normalize-space(string())') for th in tr.xpath('./th'))
                for tr in document.xpath('//table[@class="summary-item-body"]/thead/tr')
            ) == (('Supplier', 'Service ID', 'Edited', 'Changes'),)

    def test_acknowledge_audit_event_happy_path(self, data_api_client):
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

        data_api_client.get_audit_event.side_effect = lambda audit_event_id: {123: audit_event}[audit_event_id]
        response = self.client.post('/admin/services/321/updates/123/approve')
        assert response.status_code == 302
        assert_flashes(self, "The changes to service 321 were approved.")
        assert response.location == 'http://localhost/admin/services/updates/unapproved'

        data_api_client.acknowledge_service_update_including_previous.assert_called_with(
            u'321',
            123,
            'test@example.com'
        )

    def test_should_404_wrong_service_id(self, data_api_client):
        response = self.client.post('/admin/services/123/updates/321/approve')
        assert response.status_code == 404

    def test_should_403_forbidden_user_roles(self, data_api_client):
        roles_not_allowed = ('admin', 'admin-ccs-sourcing', 'buyer', 'supplier')

        for role in roles_not_allowed:
            self.user_role = role
            response = self.client.post('/admin/services/123/updates/321/approve')
            assert response.status_code == 403

    def test_should_410_already_acknowledged_event(self, data_api_client):
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

        data_api_client.get_audit_event.side_effect = lambda audit_event_id: {123: audit_event}[audit_event_id]
        response = self.client.post('/admin/services/321/updates/123/approve')
        assert response.status_code == 410

    def test_should_404_wrong_audit_event_type(self, data_api_client):
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

        data_api_client.get_audit_event.side_effect = lambda audit_event_id: {123: audit_event}[audit_event_id]
        response = self.client.post('/admin/services/321/updates/123/approve')
        assert response.status_code == 404


@mock.patch('app.main.views.service_updates.data_api_client', autospec=True)
class TestServiceStatusUpdates(LoggedInApplicationTest):

    def test_redirects_to_current_day(self, data_api_client):
        response = self.client.get(
            '/admin/service-status-updates'
        )

        assert response.status_code == 302
        assert 'http://localhost/admin/service-status-updates/20' in response.location

    def test_404s_invalid_date(self, data_api_client):
        response = self.client.get(
            '/admin/service-status-updates/invalid'
        )

        assert response.status_code == 404

    def test_should_show_updates_for_a_day_with_updates(self, data_api_client):
        data_api_client.find_audit_events.return_value = {
            'auditEvents': [
                {
                    'data': {
                        'supplierId': 93518,
                        'serviceId': 1234567890,
                        'supplierName': 'Clouded Networks',
                        'new_status': 'enabled'
                    },
                    'user': 'joeblogs',
                    'type': 'update_status',
                    'createdAt': '2016-01-01T08:49:22.999Z'
                }
            ]
        }

        response = self.client.get(
            '/admin/service-status-updates/2016-01-01'
        )

        assert response.status_code == 200

        page_contents = self._replace_whitespace(response.get_data(as_text=True))

        assert 'Friday1January2016' in page_contents
        assert '1234567890' in page_contents

    def test_should_link_to_previous_and_next_days(self, data_api_client):
        data_api_client.find_audit_events.return_value = {
            'auditEvents': []
        }

        response = self.client.get(
            '/admin/service-status-updates/2015-12-23'
        )

        page_contents = self._replace_whitespace(response.get_data(as_text=True))

        assert 'Wednesday23December2015' in page_contents

        assert 'class="next-page"' in page_contents
        assert 'Tuesday22December2015' in page_contents
        assert '/service-status-updates/2015-12-22' in page_contents

        assert 'class="previous-page"' in page_contents
        assert 'Thursday24December2015' in page_contents
        assert '/service-status-updates/2015-12-24' in page_contents

    def test_should_link_to_next_page(self, data_api_client):
        data_api_client.find_audit_events.return_value = {
            'auditEvents': [],
            'links': {
                'next': '/'
            }
        }

        response = self.client.get(
            '/admin/service-status-updates/2015-12-23'
        )

        page_contents = self._replace_whitespace(response.get_data(as_text=True))

        assert 'class="next-page"' in page_contents
        assert 'Page2' in page_contents
        assert 'ofWednesday23December2015' in page_contents
        assert '/service-status-updates/2015-12-23/page-2' in page_contents

        assert 'Nextday' in page_contents

    def test_should_link_to_previous_page(self, data_api_client):
        data_api_client.find_audit_events.return_value = {
            'auditEvents': [],
            'links': {
                'next': '/',
                'prev': '/'
            }
        }

        response = self.client.get(
            '/admin/service-status-updates/2015-12-23/page-2'
        )

        page_contents = self._replace_whitespace(response.get_data(as_text=True))

        assert 'class="previous-page"' in page_contents
        assert 'Page1' in page_contents
        assert 'ofWednesday23December2015' in page_contents
        assert '/service-status-updates/2015-12-23/page-1' in page_contents
