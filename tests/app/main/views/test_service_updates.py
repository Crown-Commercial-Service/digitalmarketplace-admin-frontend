import mock

from dmapiclient.audit import AuditTypes

from ...helpers import LoggedInApplicationTest


class TestServiceUpdates(LoggedInApplicationTest):
    @mock.patch('app.main.views.service_updates.data_api_client')
    def test_should_call_api_with_correct_params(self, data_api_client):
        data_api_client.find_audit_events.return_value = {'auditEvents': [], 'links': {}}

        response = self.client.get('/admin/service-updates?audit_date=2006-01-01&acknowledged=all')  # noqa
        assert response.status_code == 200

        data_api_client.find_audit_events.assert_called_with(
            audit_type=AuditTypes.update_service,
            audit_date='2006-01-01',
            acknowledged='all',
            page=1)

    @mock.patch('app.main.views.service_updates.data_api_client')
    def test_should_call_api_with_none_date(self, data_api_client):
        data_api_client.find_audit_events.return_value = {'auditEvents': [], 'links': {}}

        response = self.client.get('/admin/service-updates?acknowledged=all')  # noqa
        assert response.status_code == 200

        data_api_client.find_audit_events.assert_called_with(
            audit_type=AuditTypes.update_service,
            audit_date=None,
            acknowledged='all',
            page=1)

    @mock.patch('app.main.views.service_updates.data_api_client')
    def test_should_redirect_to_update_page(self, data_api_client):
        response = self.client.post(
            '/admin/service-updates/123/acknowledge',
            data={
                'acknowledged': 'false',
                'audit_date': '2010-01-05'
            }
        )

        assert response.status_code == 302
        assert 'http://localhost/admin/service-updates' in response.location
        assert 'acknowledged=false' in response.location
        assert 'audit_date=2010-01-05' in response.location

        data_api_client.acknowledge_audit_event.assert_called_with("123", 'test@example.com')

    @mock.patch('app.main.views.service_updates.data_api_client')
    def test_should_show_no_updates_if_none_returned(self, data_api_client):
        data_api_client.find_audit_events.return_value = {'auditEvents': [], 'links': {}}

        response = self.client.get('/admin/service-updates?audit_date=2006-01-01')  # noqa
        assert response.status_code == 200

        assert self._replace_whitespace('Noauditeventsfound') in self._replace_whitespace(
            response.get_data(as_text=True)
        )

        data_api_client.find_audit_events.assert_called_with(
            page=1,
            audit_date='2006-01-01',
            audit_type=AuditTypes.update_service,
            acknowledged='false')

    @mock.patch('app.main.views.service_updates.data_api_client')
    def test_should_show_no_updates_if_invalid_search(self, data_api_client):
        response = self.client.get('/admin/service-updates?audit_date=invalid')  # noqa
        assert response.status_code == 400

        assert self._replace_whitespace('Noauditeventsfound') in self._replace_whitespace(
            response.get_data(as_text=True)
        )

        assert data_api_client.find_audit_events.called is False

    @mock.patch('app.main.views.service_updates.data_api_client')
    def test_should_call_api_ack_audit_event(self, data_api_client):
        response = self.client.post('/admin/service-updates/123/acknowledge?audit_date=2010-01-01&acknowledged=all')  # noqa
        assert response.status_code == 302

        data_api_client.acknowledge_audit_event.assert_called_with(
            '123', 'test@example.com'
        )

    @mock.patch('app.main.views.service_updates.data_api_client')
    def test_should_pass_valid_page_argument_to_api(self, data_api_client):
        response = self.client.get('/admin/service-updates?page=5')
        assert response.status_code == 200

        data_api_client.find_audit_events.assert_called_with(
            page=5,
            audit_type=AuditTypes.update_service,
            acknowledged='false',
            audit_date=None
            )

    @mock.patch('app.main.views.service_updates.data_api_client')
    def test_should_not_pass_invalid_page_argument_to_api(self, data_api_client):
        response = self.client.get('/admin/service-updates?page=invalid')
        assert response.status_code == 400

        assert data_api_client.find_audit_events.called is False


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
