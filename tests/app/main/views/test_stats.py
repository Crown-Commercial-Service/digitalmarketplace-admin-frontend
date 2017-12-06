import mock
import pytest
from dmapiclient import HTTPError
from dmapiclient.audit import AuditTypes

from ...helpers import LoggedInApplicationTest


@mock.patch('app.main.views.stats.data_api_client')
class TestStats(LoggedInApplicationTest):
    def setup_method(self, method, *args, **kwargs):
        super(TestStats, self).setup_method(method, *args, **kwargs)
        self.user_role = 'admin-ccs-sourcing'

    @pytest.mark.parametrize("role,expected_code", [
        ("admin", 403),
        ("admin-ccs-category", 403),
        ("admin-ccs-sourcing", 200),
        ("admin-framework-manager", 200),
        ("admin-manager", 403),
    ])
    def test_get_page_should_only_be_accessible_to_specific_user_roles(self, data_api_client, role, expected_code):
        self.user_role = role
        response = self.client.get('/admin/statistics/g-cloud-7')
        actual_code = response.status_code
        assert actual_code == expected_code, "Unexpected response {} for role {}".format(actual_code, role)

    def test_get_stats_page(self, data_api_client):
        data_api_client.find_audit_events.return_value = {
            'auditEvents': []
        }
        response = self.client.get('/admin/statistics/g-cloud-7')

        data_api_client.find_audit_events.assert_called_once_with(
            audit_type=AuditTypes.snapshot_framework_stats,
            object_type='frameworks',
            object_id='g-cloud-7',
            per_page=1260
        )

        assert response.status_code == 200

    def test_get_stats_page_for_open_framework_includes_framework_stats(self, data_api_client):
        data_api_client.find_audit_events.return_value = {
            'auditEvents': []
        }
        data_api_client.get_framework.return_value = {
            'frameworks': {'status': 'open', 'lots': []}
        }
        response = self.client.get('/admin/statistics/g-cloud-7')

        data_api_client.get_framework_stats.assert_called_once_with('g-cloud-7')
        assert response.status_code == 200

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

        data_api_client.find_audit_events.assert_called_once_with(
            audit_type=AuditTypes.snapshot_framework_stats,
            object_type='frameworks',
            object_id='g-cloud-7',
            per_page=1260
        )

        assert response.status_code == 200
        page_without_whitespace = ''.join(response.get_data(as_text=True).split())
        assert '<span>214</span>' in page_without_whitespace  # Interested suppliers = 101+113
        assert '<span>107</span>' in page_without_whitespace  # Declaration only
        assert '<span>230</span>' in page_without_whitespace  # Completed services only 103 + 127
        assert '<span>109</span>' in page_without_whitespace  # Eligible application

    def test_get_stats_page_for_invalid_framework(self, data_api_client):
        api_response = mock.Mock()
        api_response.status_code = 404
        data_api_client.find_audit_events.side_effect = HTTPError(api_response)
        response = self.client.get('/admin/statistics/g-cloud-11')
        assert response.status_code == 404

    def test_get_stats_page_when_API_is_down(self, data_api_client):
        api_response = mock.Mock()
        api_response.status_code = 500
        data_api_client.find_audit_events.side_effect = HTTPError(api_response)
        response = self.client.get('/admin/statistics/g-cloud-7')
        assert response.status_code == 500
