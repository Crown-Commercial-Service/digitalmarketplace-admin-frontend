# coding=utf-8

import mock

from dmutils.forms import FakeCsrf

from ...helpers import LoggedInApplicationTest


class TestApplication(LoggedInApplicationTest):
    def test_main_index(self):
        response = self.client.get('/admin')
        self.assertEqual(200, response.status_code)

    def test_404(self):
        with self.app.app_context():
            response = self.client.get('/admin/not-found')
            self.assertEqual(404, response.status_code)

    def test_headers(self):
        res = self.client.get('/admin')
        assert 200 == res.status_code
        self.assertIn('Secure;', res.headers['Set-Cookie'])
        self.assertIn('DENY', res.headers['X-Frame-Options'])

    @mock.patch('app.main.views.suppliers.data_api_client')
    def test_csrf_protection(self, data_api_client):
        res = self.client.post(
            '/admin/suppliers/users/1/activate',
            data={
                'source': '/',
                'csrf_token': FakeCsrf.valid_token,
            }
        )
        assert res.status_code < 400
        res = self.client.post(
            '/admin/suppliers/users/1/activate',
            data={
                'source': '/',
            }
        )
        assert 400 == res.status_code
