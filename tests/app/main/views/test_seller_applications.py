from ...helpers import BaseApplicationTest, LoggedInApplicationTest
import mock


class TestApplicationAdmin(LoggedInApplicationTest):
    @mock.patch('app.main.views.applications.data_api_client')
    @mock.patch('app.main.views.applications.render_component')
    def test_applications_approval_page_renders(self, render_component, data_api_client):
        render_component.return_value.get_props.return_value = {}
        render_component.return_value.get_slug.return_value = 'slug'

        response = self.client.get('/admin/applications')
        assert response.status_code == 200
