from flask import json
import mock

from ..helpers import BaseApplicationTest


class TestStatus(BaseApplicationTest):

    @mock.patch('app.status.views.data_api_client')
    def test_status_ok(self, data_api_client):

        data_api_client.get_status.return_value = {"status": "ok"}

        response = self.client.get('/admin/_status')
        self.assertEquals(200, response.status_code)

        json_data = json.loads(response.get_data())

        self.assertEquals("ok", "{}".format(json_data['status']))
        self.assertEquals("ok", "{}".format(
            json_data['api_status']['status']))

    @mock.patch('app.status.views.data_api_client')
    def test_status_error(self, data_api_client):

        data_api_client.get_status.return_value = {
            'status': 'error',
            'app_version': None,
            'message': 'Cannot connect to (Data) API'
        }

        response = self.client.get('/admin/_status')
        self.assertEquals(500, response.status_code)

        json_data = json.loads(response.get_data())

        self.assertEquals("error", "{}".format(json_data['status']))
