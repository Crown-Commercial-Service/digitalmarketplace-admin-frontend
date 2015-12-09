from nose.tools import assert_in
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
            object_type='frameworks',
            object_id='g-cloud-7',
            per_page=1260
        )

        self.assertEquals(200, response.status_code)

    def test_supplier_counts_on_stats_page(self, data_api_client):
        data_api_client.find_audit_events.return_value = {
            "auditEvents": [
                {
                    "acknowledged": False,
                    "createdAt": "2015-12-09T14:45:20.969220Z",
                    "data": {
                        "interested_suppliers": [
                            {
                                "count": 101,
                                "declaration_status": None,
                                "has_completed_services": False
                            },
                            {
                                "count": 103,
                                "declaration_status": None,
                                "has_completed_services": True
                            },
                            {
                                "count": 107,
                                "declaration_status": "complete",
                                "has_completed_services": False
                            },
                            {
                                "count": 109,
                                "declaration_status": "complete",
                                "has_completed_services": True
                            },
                            {
                                "count": 113,
                                "declaration_status": "started",
                                "has_completed_services": False
                            },
                            {
                                "count": 127,
                                "declaration_status": "started",
                                "has_completed_services": True
                            }
                        ],
                        "services": [],
                        "supplier_users": [],
                    }
                }
            ]
        }

        response = self.client.get('/admin/statistics/g-cloud-7')

        data_api_client.find_audit_events.assert_called_with(
            audit_type=AuditTypes.snapshot_framework_stats,
            object_type='frameworks',
            object_id='g-cloud-7',
            per_page=1260
        )

        self.assertEquals(200, response.status_code)
        page_without_whitespace = ''.join(response.get_data(as_text=True).split())
        assert_in('<span>214</span>', page_without_whitespace)  # Interested suppliers = 101+113
        assert_in('<span>107</span>', page_without_whitespace)  # Declaration only
        assert_in('<span>230</span>', page_without_whitespace)  # Completed services only 103 + 127
        assert_in('<span>109</span>', page_without_whitespace)  # Eligible application

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
