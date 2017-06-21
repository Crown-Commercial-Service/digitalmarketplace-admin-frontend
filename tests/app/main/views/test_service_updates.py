# -*- coding: utf-8 -*-
import mock
import pytest
from lxml import html

from dmapiclient.audit import AuditTypes

from ...helpers import LoggedInApplicationTest


@mock.patch('app.main.views.service_updates.data_api_client', autospec=True)
class TestServiceUpdates(LoggedInApplicationTest):
    @pytest.mark.parametrize('audit_events,expected_table_contents,expected_count', (
        (
            (
                ('2012-07-15T18:03:43.061077Z', '1123456789012351', u'Company name', '240697', '240680'),
                ('2016-03-05T10:42:16.061077Z', '1123456789012348', u'Testing Limited', '240699', '240682'),
                ('2017-04-25T14:43:46.061077Z', '597637931594387', u'Ideal Health £', '240701', '240684'),
            ),
            (
                ('Company name', '1123456789012351', '19:03:43 15 July', '/admin/services/compare/240697...240680'),
                (u'Testing Limited', '1123456789012348', '10:42:16 5 March', '/admin/services/compare/240699...240682'),
                (u'Ideal Health £', '597637931594387', '15:43:46 25 April', '/admin/services/compare/240701...240684'),
            ),
            '3 services',
        ),
        (
            (
                ('2012-07-15T18:03:43.061077Z', '597637931590002', 'Company name', '240697', '240680'),
                ('2016-03-05T10:42:16.061077Z', '597637931590001', 'Ideal Health', '240699', '240682'),
            ),
            (
                ('Company name', '597637931590002', '19:03:43 15 July', '/admin/services/compare/240697...240680'),
                ('Ideal Health', '597637931590001', '10:42:16 5 March', '/admin/services/compare/240699...240682'),
            ),
            '2 services',
        ),
        (
            (),
            (),
            '0 services',
        ),
        (
            (
                ('2012-07-15T18:03:43.061077Z', '597637931590002', 'Company name', '240697', '240680'),
            ),
            (
                ('Company name', '597637931590002', '19:03:43 15 July', '/admin/services/compare/240697...240680'),
            ),
            '1 service',
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

        response = self.client.get('/admin/services/updates/unacknowledged')

        assert response.status_code == 200
        document = html.fromstring(response.get_data(as_text=True))

        assert tuple(
            tuple(
                td.xpath('normalize-space(string())') for td in tr.xpath('./td')[:-1]
            ) + (tr.xpath('./td[last()]//a/@href')[0],)
            for tr in document.xpath('//table[@class="summary-item-body"]/tbody/tr')
        ) == expected_table_contents

        assert document.xpath('normalize-space(string(//*[@class="search-summary"]))') == expected_count

        if (audit_events != ()):
            assert tuple(
                tuple(th.xpath('normalize-space(string())') for th in tr.xpath('./th'))
                for tr in document.xpath('//table[@class="summary-item-body"]/thead/tr')
            ) == (('Supplier', 'Service ID', 'Edited', 'Changes'),)

    @pytest.mark.parametrize('audit_events,expected_table_contents,expected_count', (
        (
            (
                (5678, '2012-07-15T18:03:43.061077Z', 'User 1', '1123456789012351',
                 u'Company name', '240697', '240680'),
                (4321, '2016-03-05T10:42:16.061077Z', 'User 2', '1123456789012348',
                 u'Testing Limited', '240699', '240682'),
                (1234, '2017-04-25T14:43:46.061077Z', 'User 1', '597637931594387',
                 u'Ideal Health £', '240701', '240684'),
            ),
            (
                (u'Company name', '1123456789012351', '19:03:43 15 July', '/admin/services/compare/240697...240680'),
                (u'Testing Limited', '1123456789012348', '10:42:16 5 March', '/admin/services/compare/240699...240682'),
                (u'Ideal Health £', '597637931594387', '15:43:46 25 April', '/admin/services/compare/240701...240684'),
            ),
            '3 services',
        ),
        (
            (),
            (),
            '0 services',
        ),
        (
            (
                (3456, '2012-07-15T18:03:43.061077Z', 'user 1', '597637931590002', 'Company name', '240697', '240680'),
            ),
            (
                ('Company name', '597637931590002', '19:03:43 15 July', '/admin/services/compare/240697...240680'),
            ),
            '1 service',
        ),
    ))
    def test_should_show_acknowledged_services(
            self, data_api_client, audit_events, expected_table_contents, expected_count):
        data_api_client.find_audit_events.return_value = {
            "auditEvents": [
                {
                    "data": {
                        "oldArchivedServiceId": old_archived_service_id,
                        "newArchivedServiceId": new_archived_service_id,
                        "supplierName": supplier_name,
                        "serviceId": service_id
                    },
                    "id": id,
                    "acknowledgedAt": date_string,
                    "acknowledgedBy": acknowledged_by
                } for (
                    id, date_string, acknowledged_by, service_id, supplier_name,
                    old_archived_service_id, new_archived_service_id
                ) in audit_events
            ],
            "links": {},
        }

        response = self.client.get('/admin/services/updates')

        assert response.status_code == 200
        document = html.fromstring(response.get_data(as_text=True))

        assert tuple(
            tuple(
                td.xpath('normalize-space(string())') for td in tr.xpath('./td')[:-1]
            ) + (tr.xpath('./td[last()]//a/@href')[0],)
            for tr in document.xpath('//table[@class="summary-item-body"]/tbody/tr')
        ) == expected_table_contents

        assert document.xpath('normalize-space(string(//*[@class="search-summary"]))') == expected_count

        if (audit_events != ()):
            assert tuple(
                tuple(th.xpath('normalize-space(string())') for th in tr.xpath('./th'))
                for tr in document.xpath('//table[@class="summary-item-body"]/thead/tr')
            ) == (('Supplier', 'Service ID', 'Acknowledged', 'Changes'),)

    def test_should_show_no_updates_if_none_returned(self, data_api_client):
        data_api_client.find_audit_events.return_value = {'auditEvents': [], 'links': {}}

        response = self.client.get('/admin/services/updates')  # noqa
        assert response.status_code == 200

        assert self._replace_whitespace('Noauditeventsfound') in self._replace_whitespace(
            response.get_data(as_text=True)
        )


@mock.patch('app.main.views.service_updates.data_api_client')
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
