from nose.tools import assert_in
import mock

from dmapiclient import HTTPError
from dmapiclient.audit import AuditTypes
from ...helpers import LoggedInApplicationTest


@mock.patch('app.main.views.stats.data_api_client')
class TestStats(LoggedInApplicationTest):
    def test_get_stats_page(self, data_api_client):
        response = self.client.get('/admin/statistics/applications')
        self.assertEqual(200, response.status_code)

    def test_supplier_counts_on_stats_page(self, data_api_client):
        data_api_client.req.metrics().applications().history().get.return_value = {
            "approve_application_count": [
                {
                    "ts": "2017-01-13T00:00:00+00:00",
                    "value": 1
                },
                {
                    "ts": "2017-01-14T00:00:00+00:00",
                    "value": 2
                },
                {
                    "ts": "2017-01-15T00:00:00+00:00",
                    "value": 3
                }
            ],
            "create_application_count": [
                {
                    "ts": "2017-01-04T00:00:00+00:00",
                    "value": 4
                },

            ],
            "revert_application_count": [
                {
                    "ts": "2017-01-16T00:00:00+00:00",
                    "value": 5
                },

            ],
            "submit_application_count": [
                {
                    "ts": "2017-01-19T00:00:00+00:00",
                    "value": 6
                },

            ],
            "unassessed_domain_count": [
                {
                    "ts": "2017-01-16T00:00:00+00:00",
                    "value": 7
                }
            ]
        }

        data_api_client.req.metrics().domains().get.return_value = [
            {
                "domain": "Change, Training and Transformation",
                "timestamp": "2017-02-01T16:36:17+11:00",
                "unassessed": 1
            },
            {
                "domain": "Emerging technology",
                "timestamp": "2017-02-01T16:36:17+11:00",
                "unassessed": 1
            },
            {
                "assessed": 1,
                "domain": "User research and Design",
                "timestamp": "2017-02-01T16:36:17+11:00"
            },
            {
                "assessed": 1,
                "domain": "Strategy and Policy",
                "timestamp": "2017-02-01T16:36:17+11:00",
                "unassessed": 1
            }
        ]
        response = self.client.get('/admin/statistics/applications')

        data_api_client.req.metrics().applications().history().get.assert_called()
        data_api_client.req.metrics().domains().get.assert_called()

        self.assertEqual(200, response.status_code)
        page_without_whitespace = ''.join(response.get_data(as_text=True).split())
        assert_in('<span>7</span>', page_without_whitespace)

    def test_get_stats_page_when_API_is_down(self, data_api_client):
        api_response = mock.Mock()
        api_response.status_code = 500
        data_api_client.req.metrics().applications().history().get.side_effect = HTTPError(api_response)
        response = self.client.get('/admin/statistics/applications')
        self.assertEqual(500, response.status_code)
