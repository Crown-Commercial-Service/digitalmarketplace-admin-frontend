from ...helpers import LoggedInApplicationTest
import pytest
import mock
import csv


class TestDirectAwardView(LoggedInApplicationTest):
    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.direct_award.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    @pytest.mark.parametrize("role,expected_code", [
        ("admin", 403),
        ("admin-manager", 403),
        ("admin-ccs-category", 200),
        ("admin-ccs-sourcing", 200),
        ("admin-framework-manager", 200),
    ])
    def test_outcomes_csv_download_permissions(self, role, expected_code):
        self.user_role = role
        response = self.client.get('/admin/direct-award/outcomes')
        actual_code = response.status_code
        assert actual_code == expected_code, "Unexpected response {} for role {}".format(actual_code, role)

    def test_outcomes_csv_download_content_type(self):
        self.user_role = 'admin-ccs-sourcing'
        response = self.client.get('/admin/direct-award/outcomes')
        assert response.status_code == 200
        assert response.content_type == 'text/csv; charset=utf-8'
        response_data = str(response.data, 'utf-8').splitlines()  # convert byte-string to string
        assert csv.reader(response_data)  # checks if CSV is valid
