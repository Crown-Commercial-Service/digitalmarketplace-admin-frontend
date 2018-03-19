from flask import json
import mock

from ..helpers import BaseApplicationTest


class TestStatus(BaseApplicationTest):

    @mock.patch('app.status.views.data_api_client')
    def test_should_return_200_from_elb_status_check(self, data_api_client):
        status_response = self.client.get('/admin/_status?ignore-dependencies')
        assert status_response.status_code == 200
        assert data_api_client.call_args_list == []

    @mock.patch('app.status.views.data_api_client')
    def test_status_ok(self, data_api_client):

        data_api_client.get_status.return_value = {"status": "ok"}

        response = self.client.get('/admin/_status')
        assert response.status_code == 200

        json_data = json.loads(response.get_data())

        assert "{}".format(json_data['status']) == "ok"
        assert "{}".format(json_data['api_status']['status']) == "ok"

    @mock.patch('app.status.views.data_api_client')
    def test_status_error(self, data_api_client):
        data_api_client.get_status.return_value = {
            'status': 'error',
            'app_version': None,
            'message': 'Cannot connect to Data API'
        }

        response = self.client.get('/admin/_status')
        assert response.status_code == 500

        json_data = json.loads(response.get_data())

        assert "{}".format(json_data['status']) == "error"
