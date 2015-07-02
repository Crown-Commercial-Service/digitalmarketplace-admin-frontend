# coding=utf-8

from ...helpers import LoggedInApplicationTest


class TestApplication(LoggedInApplicationTest):
    def test_main_index(self):
        response = self.client.get('/admin')
        self.assertEquals(200, response.status_code)

    def test_404(self):
        with self.app.app_context():
            response = self.client.get('/admin/not-found')
            self.assertEquals(404, response.status_code)

    def test_index_is_404(self):
        response = self.client.get('/')
        self.assertEquals(404, response.status_code)

    def test_headers(self):
        res = self.client.get('/admin')
        assert 200 == res.status_code
        self.assertIn('Secure;', res.headers['Set-Cookie'])
        self.assertIn('DENY', res.headers['X-Frame-Options'])

    def test_response_headers(self):
        response = self.client.get('/admin')

        assert (
            response.headers['cache-control'] ==
            "no-cache"
        )
