# coding=utf-8

import mock
import pytest

from ...helpers import LoggedInApplicationTest


class TestApplication(LoggedInApplicationTest):
    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.services.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()
        self.data_api_client.find_frameworks.return_value = {"frameworks": []}

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    def test_main_index(self):
        response = self.client.get('/admin')
        assert response.status_code == 200
        assert self.data_api_client.find_frameworks.call_args_list == [mock.call()]

    def test_404(self):
        response = self.client.get('/admin/not-found')
        assert response.status_code == 404

    def test_headers(self):
        res = self.client.get('/admin')
        assert res.status_code == 200
        assert any('Secure;' in c for c in res.headers.getlist('Set-Cookie'))
        assert 'DENY' in res.headers['X-Frame-Options']
        assert self.data_api_client.find_frameworks.call_args_list == [mock.call()]

    def test_response_headers(self):
        response = self.client.get('/admin')
        assert response.headers['cache-control'] == "no-cache"
        assert self.data_api_client.find_frameworks.call_args_list == [mock.call()]

    @pytest.mark.parametrize('role', ['buyer', 'supplier'])
    def test_only_admin_users_are_allowed(self, role):
        self.user_role = role
        response = self.client.get('/admin')

        assert response.status_code == 302
        assert response.location == 'http://localhost/user/login?next=%2Fadmin'
        assert self.data_api_client.find_frameworks.call_args_list == []
