from flask import json
from requests import Response
import mock

from ..helpers import BaseApplicationTest


class TestStatus(BaseApplicationTest):

    @mock.patch('app.status.views.data_api_client')
    def test_status_ok(self, data_api_client):
        response = Response()
        response.status_code = 200
        response._content = json.dumps({
            'status': 'ok',
            'app_version': None,
            'api_status': 'ok'
        }).encode('utf-8')

        data_api_client.get_status.return_value = response

        response = self.client.get('/_status')
        self.assertEquals(200, response.status_code)

        json_data = json.loads(response.get_data())

        self.assertEquals("ok", "{}".format(json_data['status']))
        self.assertEquals("ok", "{}".format(
            json_data['api_status']['status']))

    @mock.patch('app.status.views.data_api_client')
    def test_status_error(self, data_api_client):
        response = Response()
        response.status_code = 500
        response._content = json.dumps({
            'status': 'error',
            'app_version': None,
            'message': 'Cannot connect to (Data) API'
        }).encode('utf-8')

        # set up the service_loader to return a 500 status-code response
        data_api_client.get_status.return_value = response

        response = self.client.get('/_status')
        self.assertEquals(500, response.status_code)

        json_data = json.loads(response.get_data())

        self.assertEquals("error", "{}".format(json_data['status']))
