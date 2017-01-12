# coding=utf-8

import mock

from dmutils.forms import FakeCsrf

from ...helpers import LoggedInApplicationTest
import json

import responses

from app import data_api_client


class TestApplication(LoggedInApplicationTest):
    @responses.activate
    def test_convert_to_seller(self):
        BASE_URL = data_api_client.base_url

        csrf = 'abc123'

        with self.client.session_transaction() as sess:
            sess['_csrf_token'] = csrf

        expected_from_api = {
            'application': {
                'id': 99
            }
        }

        responses.add(
            responses.POST, BASE_URL + '/applications/99/approve',
            body=json.dumps(expected_from_api),
            content_type='application/json',
        )

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
