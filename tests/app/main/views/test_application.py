# coding=utf-8

import mock
import pytest

from ...helpers import LoggedInApplicationTest


class TestApplication(LoggedInApplicationTest):
    @mock.patch('app.main.views.services.data_api_client')
    def test_main_index(self, data_api_client):
        data_api_client.get_frameworks.return_value = {"frameworks": []}
        response = self.client.get('/admin')
        assert response.status_code == 200

    def test_404(self):
        with self.app.app_context():
            response = self.client.get('/admin/not-found')
            assert response.status_code == 404

    @mock.patch('app.main.views.services.data_api_client')
    def test_headers(self, data_api_client):
        data_api_client.get_frameworks.return_value = {"frameworks": []}
        res = self.client.get('/admin')
        assert res.status_code == 200
        assert 'Secure;' in res.headers['Set-Cookie']
        assert 'DENY' in res.headers['X-Frame-Options']

    @mock.patch('app.main.views.services.data_api_client')
    def test_response_headers(self, data_api_client):
        data_api_client.get_frameworks.return_value = {"frameworks": []}
        response = self.client.get('/admin')

        assert response.headers['cache-control'] == "no-cache"

    @pytest.mark.parametrize('role', ['buyer', 'supplier'])
    @mock.patch('app.main.views.services.data_api_client')
    def test_only_admin_users_are_allowed(self, data_api_client, role):
        self.user_role = role
        data_api_client.get_frameworks.return_value = {"frameworks": []}
        response = self.client.get('/admin')

        assert response.status_code == 302
        assert response.location == 'http://localhost/user/login?next=%2Fadmin'
