from datetime import datetime

from ..helpers import LoggedInApplicationTest


class TestActivity(LoggedInApplicationTest):

    def test_should_render_activity_page_with_default_date(self):
        today = datetime.now().strftime("%d/%m/%Y")

        response = self.client.get('/admin/activity')
        self.assertEquals(200, response.status_code)

        self.assertIn(
            today,
            response.get_data(as_text=True)
        )

    def test_should_render_correct_form_defaults(self):
        response = self.client.get('/admin/activity')
        self.assertEquals(200, response.status_code)

        self.assertIn(
            '<input id="csrf_token" name="csrf_token" type="hidden" value="',
            response.get_data(as_text=True)
        )

        self.assertIn(
            '<input class="filter-field-text" type="text" name="activity-date" id="activity-date" value="">',
            response.get_data(as_text=True)
        )

        self.assertIn(
            self._replace_whitespace('<input name="acknowledged" value="acknowledged" id="acknowledged-1" type="radio" aria-controls="" checked>'),  # noqa
            self._replace_whitespace(response.get_data(as_text=True))
        )
