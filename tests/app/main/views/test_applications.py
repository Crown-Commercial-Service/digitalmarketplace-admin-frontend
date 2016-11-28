# coding=utf-8

import mock

from dmutils.forms import FakeCsrf

from ...helpers import LoggedInApplicationTest
import json


class TestApplication(LoggedInApplicationTest):
    @mock.patch('app.main.views.applications.data_api_client')
    def test_convert_to_seller(self, data_api_client):
        csrf = 'abc123'

        with self.client.session_transaction() as sess:
            sess['_csrf_token'] = csrf

        data_api_client.approve_application.return_value = \
            {
                'application': {
                    'id': 99
                }
            }

        res = self.client.post(
            '/admin/applications/convert_to_seller',
            data=json.dumps({
                'id': 99,
            }),
            content_type='application/json',
            headers={
                'x-csrftoken': csrf
            }
        )
        assert res.status_code < 400
        data_api_client.approve_application.assert_called_with(99)
