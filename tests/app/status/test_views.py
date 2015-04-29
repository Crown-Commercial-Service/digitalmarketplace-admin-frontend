from flask import json
from requests import Response
import mock

from ..helpers import BaseApplicationTest


class TestStatus(BaseApplicationTest):
    @mock.patch("app.status.views.ServiceLoader")
    def test_status_ok(self, ServiceLoader):
        ServiceLoader.return_value = mock.Mock()
        response = Response()
        response.status_code = 200
        response._content = json.dumps({
            'status': 'ok',
            'app_version': None,
            'api_status': 'ok'
        })
        ServiceLoader.return_value.status.return_value = response

        status_response = self.client.get('/_status')

        self.assertEquals(200, status_response.status_code)

        json_data = json.loads(status_response.get_data())

        self.assertEquals("ok", "{}".format(json_data['status']))
        self.assertEquals("ok", "{}".format(json_data['api_status']))

    @mock.patch("app.status.views.ServiceLoader")
    def test_status_error(self, ServiceLoader):
        ServiceLoader.return_value = mock.Mock()
        response = Response()
        response.status_code = 500
        response._content = json.dumps({
            'status': 'error',
            'app_version': None,
            'message': 'Cannot connect to API'
        })

        # set up the service_loader to return a 500 status-code response
        ServiceLoader.return_value.status.return_value = response

        response = self.client.get('/_status')
        self.assertEquals(500, response.status_code)
