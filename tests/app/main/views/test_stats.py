import mock

from dmutils.apiclient import HTTPError
from dmutils.audit import AuditTypes
from ...helpers import LoggedInApplicationTest


@mock.patch('app.main.views.stats.data_api_client')
class TestStats(LoggedInApplicationTest):

    def test_get_stats_page(self, data_api_client):
        data_api_client.find_audit_events.return_value = {
            'auditEvents': []
        }
        response = self.client.get('/admin/statistics/g-cloud-7')

        data_api_client.find_audit_events.assert_called_with(
            audit_type=AuditTypes.snapshot_framework_stats,
            per_page=1260
        )

        self.assertEquals(200, response.status_code)

    def test_get_stats_page_for_invalid_framework(self, data_api_client):
        api_response = mock.Mock()
        api_response.status_code = 404
        data_api_client.find_audit_events.side_effect = HTTPError(api_response)
        response = self.client.get('/admin/statistics/g-cloud-11')
        self.assertEquals(404, response.status_code)

    def test_get_stats_page_when_API_is_down(self, data_api_client):
        api_response = mock.Mock()
        api_response.status_code = 500
        data_api_client.find_audit_events.side_effect = HTTPError(api_response)
        response = self.client.get('/admin/statistics/g-cloud-7')
        self.assertEquals(500, response.status_code)
