from flask import json, Response
import mock

from ..helpers import BaseApplicationTest


class TestStatus(BaseApplicationTest):
    @mock.patch("app.status.views.ServiceLoader")
    def test_status_ok(self, ServiceLoader):
        ServiceLoader.return_value = mock.Mock()
        ServiceLoader.return_value.status.return_value = Response(
            json.dumps({
                'status': 'ok',
                'app_version': None,
                'api_status': 'ok'
            }),
            200
        )

        response = self.client.get('/_status')

        self.assertEquals(200, response.status_code)

        json_data = json.loads(response.get_data())

        self.assertEquals("ok", json_data['status'])
        self.assertEquals("ok", json_data['api_status'])

    @mock.patch("app.status.views.ServiceLoader")
    def test_status_error(self, ServiceLoader):
        ServiceLoader.return_value = mock.Mock()

        # set up the service_loader to return a 500 status-code response
        ServiceLoader.return_value.status.return_value = Response(
            json.dumps({
                'status': 'error',
                'message': 'Cannot connect to API'
            }),
            500,
        )

        response = self.client.get('/_status')
        self.assertEquals(500, response.status_code)
