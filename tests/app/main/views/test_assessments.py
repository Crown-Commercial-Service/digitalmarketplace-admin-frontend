import mock
from ...helpers import LoggedInApplicationTest


class TestAssessments(LoggedInApplicationTest):
    @mock.patch('app.main.views.assessments.data_api_client')
    @mock.patch('app.main.views.assessments.render_component')
    def test_assessment_list(self, render_component, data_api_client):
        render_component.return_value.get_props.return_value = {}
        render_component.return_value.get_slug.return_value = 'slug'

        response = self.client.get('/admin/assessments')
        assert response.status_code == 200
