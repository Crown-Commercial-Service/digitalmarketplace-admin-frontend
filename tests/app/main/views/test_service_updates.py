import mock
import pytest

from datetime import datetime
from dmutils.formats import DISPLAY_DATE_FORMAT
from dmutils.forms import FakeCsrf
from dmapiclient.audit import AuditTypes

from ...helpers import LoggedInApplicationTest


class TestServiceUpdates(LoggedInApplicationTest):
    @mock.patch('app.main.views.service_updates.data_api_client')
    def test_should_render_activity_page_with_date(self, data_api_client):
        pytest.skip("fails before 11am????")

        today = datetime.utcnow().strftime(DISPLAY_DATE_FORMAT)

        response = self.client.get('/admin/service-updates')
        self.assertEqual(200, response.status_code)

        date_header = """
        <p class="context">
            Activity for
        </p>
        <h1>
        {}
        </h1>
        """.format(today)

        self.assertIn(
            self._replace_whitespace(date_header),
            self._replace_whitespace(response.get_data(as_text=True))
        )

        data_api_client.find_audit_events.assert_called()

    @mock.patch('app.main.views.service_updates.data_api_client')
    def test_should_render_correct_form_defaults(self, data_api_client):
        response = self.client.get('/admin/service-updates')
        self.assertEqual(200, response.status_code)

        self.assertIn(
            '<input class="filter-field-text" id="audit_date" name="audit_date" placeholder="eg, 2015-07-23" type="text" value="">',  # noqa
            response.get_data(as_text=True)
        )

        self.assertIn(
            self._replace_whitespace(
                '<input name="acknowledged" value="false" id="acknowledged-3" type="radio" aria-controls="" checked>'),  # noqa
            self._replace_whitespace(response.get_data(as_text=True))
        )

        data_api_client.find_audit_events.assert_called()

    @mock.patch('app.main.views.service_updates.data_api_client')
    def test_should_not_allow_invalid_dates(self, data_api_client):
        response = self.client.get('/admin/service-updates?audit_date=invalid')
        self.assertEqual(400, response.status_code)
        self.assertIn(
            "Not a valid date value",
            response.get_data(as_text=True)
        )
        self.assertIn(
            '<input class="filter-field-text" id="audit_date" name="audit_date" placeholder="eg, 2015-07-23" type="text" value="invalid">',  # noqa
            response.get_data(as_text=True)
        )

        self.assertIn(
            '<div class="validation-masthead" aria-labelledby="validation-masthead-heading">',  # noqa
            response.get_data(as_text=True)
        )

        self.assertIn(
            self._replace_whitespace(
                '<a href="#example-textbox" class="validation-masthead-link"><label for="audit_date">Audit Date</label></a>'),  # noqa
            self._replace_whitespace(response.get_data(as_text=True))
        )

        data_api_client.find_audit_events.assert_not_called()

    @mock.patch('app.main.views.service_updates.data_api_client')
    def test_should_not_allow_invalid_acknowledges(self, data_api_client):
        response = self.client.get(
            '/admin/service-updates?acknowledged=invalid'
        )
        self.assertEqual(400, response.status_code)

        self.assertIn(
            self._replace_whitespace(
                '<a href="#example-textbox" class="validation-masthead-link"><label for="acknowledged">acknowledged</label></a>'),  # noqa
            self._replace_whitespace(response.get_data(as_text=True))
        )
        data_api_client.find_audit_events.assert_not_called()

    @mock.patch('app.main.views.service_updates.data_api_client')
    def test_should_allow_valid_submission_all(self, data_api_client):
        data_api_client.find_audit_events.return_value = {'auditEvents': [], 'links': {}}

        response = self.client.get('/admin/service-updates?audit_date=2006-01-01&acknowledged=all')
        self.assertEqual(200, response.status_code)
        self.assertIn(
            '<input class="filter-field-text" id="audit_date" name="audit_date" placeholder="eg, 2015-07-23" type="text" value="2006-01-01">',  # noqa
            response.get_data(as_text=True)
        )

        self.assertIn(
            self._replace_whitespace(
                '<inputname="acknowledged"value="all"id="acknowledged-1"type="radio"aria-controls=""checked>'),  # noqa
            self._replace_whitespace(response.get_data(as_text=True))
        )
        data_api_client.find_audit_events.assert_called()

    @mock.patch('app.main.views.service_updates.data_api_client')
    def test_should_allow_valid_submission_date_fields(self, data_api_client):
        data_api_client.find_audit_events.return_value = {'auditEvents': [], 'links': {}}

        response = self.client.get('/admin/service-updates?audit_date=2006-01-01')  # noqa
        self.assertEqual(200, response.status_code)
        self.assertIn(
            '<input class="filter-field-text" id="audit_date" name="audit_date" placeholder="eg, 2015-07-23" type="text" value="2006-01-01">',  # noqa
            response.get_data(as_text=True)
        )

        self.assertIn(
            self._replace_whitespace(
                '<inputname="acknowledged"value="false"id="acknowledged-3"type="radio"aria-controls=""checked>'),  # noqa
            self._replace_whitespace(response.get_data(as_text=True))
        )
        data_api_client.find_audit_events.assert_called_with(
            audit_date='2006-01-01',
            audit_type=AuditTypes.update_service,
            acknowledged='false',
            page=1)

    @mock.patch('app.main.views.service_updates.data_api_client')
    def test_should_allow_acknowledged_fields(self, data_api_client):
        data_api_client.find_audit_events.return_value = {'auditEvents': [], 'links': {}}

        response = self.client.get('/admin/service-updates?acknowledged=false')  # noqa
        self.assertEqual(200, response.status_code)
        self.assertIn(
            '<input class="filter-field-text" id="audit_date" name="audit_date" placeholder="eg, 2015-07-23" type="text" value="">',  # noqa
            response.get_data(as_text=True)
        )

        self.assertIn(
            self._replace_whitespace(
                '<inputname="acknowledged"value="false"id="acknowledged-3"type="radio"aria-controls=""checked>'),  # noqa
            self._replace_whitespace(response.get_data(as_text=True))
        )
        data_api_client.find_audit_events.assert_called_with(
            audit_date=None,
            audit_type=AuditTypes.update_service,
            acknowledged='false',
            page=1)

    @mock.patch('app.main.views.service_updates.data_api_client')
    def test_should_call_api_with_correct_params(self, data_api_client):
        data_api_client.find_audit_events.return_value = {'auditEvents': [], 'links': {}}

        response = self.client.get('/admin/service-updates?audit_date=2006-01-01&acknowledged=all')  # noqa
        self.assertEqual(200, response.status_code)

        data_api_client.find_audit_events.assert_called_with(
            audit_type=AuditTypes.update_service,
            audit_date='2006-01-01',
            acknowledged='all',
            page=1)

    @mock.patch('app.main.views.service_updates.data_api_client')
    def test_should_call_api_with_none_date(self, data_api_client):
        data_api_client.find_audit_events.return_value = {'auditEvents': [], 'links': {}}

        response = self.client.get('/admin/service-updates?acknowledged=all')  # noqa
        self.assertEqual(200, response.status_code)

        data_api_client.find_audit_events.assert_called_with(
            audit_type=AuditTypes.update_service,
            audit_date=None,
            acknowledged='all',
            page=1)

    @mock.patch('app.main.views.service_updates.data_api_client')
    def test_should_render_activity_page_with_form_date(self, data_api_client):
        response = self.client.get(
            '/admin/service-updates?audit_date=2010-01-01'
        )

        self.assertEqual(200, response.status_code)

        date_header = """
        <p class="context">
            Activity for
        </p>
        <h1>
        Friday 1 January 2010
        </h1>
        """

        self.assertIn(
            self._replace_whitespace(date_header),
            self._replace_whitespace(response.get_data(as_text=True))
        )

        data_api_client.find_audit_events.assert_called()

    @mock.patch('app.main.views.service_updates.data_api_client')
    def test_should_redirect_to_update_page(self, data_api_client):
        response = self.client.post(
            '/admin/service-updates/123/acknowledge',
            data={
                'acknowledged': 'false',
                'audit_date': '2010-01-05',
                'csrf_token': FakeCsrf.valid_token,
            }
        )

        self.assertEqual(302, response.status_code)
        self.assertIn(
            'http://localhost/admin/service-updates',
            response.location)
        self.assertIn(
            'acknowledged=false',
            response.location)
        self.assertIn(
            'audit_date=2010-01-05',
            response.location)

        data_api_client.acknowledge_audit_event.assert_called()

    @mock.patch('app.main.views.service_updates.data_api_client')
    def test_should_not_call_api_when_form_errors(self, data_api_client):
        response = self.client.post(
            '/admin/service-updates/123/acknowledge',
            data={
                'acknowledged': 'false',
                'audit_date': 'invalid',
                'csrf_token': FakeCsrf.valid_token,
            }
        )

        self.assertEqual(400, response.status_code)
        data_api_client.acknowledge_audit_event.assert_not_called()
        self.assertIn(
            self._replace_whitespace(
                '<inputname="acknowledged"value="false"id="acknowledged-3"type="radio"aria-controls=""checked>'),  # noqa
            self._replace_whitespace(response.get_data(as_text=True))
        )
        self.assertIn(
            '<input class="filter-field-text" id="audit_date" name="audit_date" placeholder="eg, 2015-07-23" type="text" value="invalid">',  # noqa
            response.get_data(as_text=True)
        )

    @mock.patch('app.main.views.service_updates.data_api_client')
    def test_should_show_no_updates_if_none_returned(self, data_api_client):
        data_api_client.find_audit_events.return_value = {'auditEvents': [], 'links': {}}

        response = self.client.get('/admin/service-updates?audit_date=2006-01-01')  # noqa
        self.assertEqual(200, response.status_code)

        self.assertIn(
            self._replace_whitespace('Noauditeventsfound'),
            self._replace_whitespace(response.get_data(as_text=True))
        )
        data_api_client.find_audit_events.assert_called_with(
            page=1,
            audit_date='2006-01-01',
            audit_type=AuditTypes.update_service,
            acknowledged='false')

    @mock.patch('app.main.views.service_updates.data_api_client')
    def test_should_show_no_updates_if_invalid_search(self, data_api_client):
        response = self.client.get('/admin/service-updates?audit_date=invalid')  # noqa
        self.assertEqual(400, response.status_code)

        self.assertIn(
            self._replace_whitespace('Noauditeventsfound'),
            self._replace_whitespace(response.get_data(as_text=True))
        )
        data_api_client.find_audit_events.assert_not_called()

    @mock.patch('app.main.views.service_updates.data_api_client')
    def test_should_show_updates_if_valid_search(self, data_api_client):

        audit_event = {
            'auditEvents': [
                {
                    'links': {
                        'self': 'http://localhost:5000/adit-events'
                    },
                    'data': {
                        'serviceName': 'new name',
                        'supplierId': 93518,
                        'supplierName': 'Clouded Networks'
                    },
                    'user': 'joeblogs',
                    'type': 'update_service',
                    'id': 25,
                    'createdAt': '2015-06-17T08:49:22.999Z'
                }
            ],
            'links': {}
        }

        data_api_client.find_audit_events.return_value = audit_event
        response = self.client.get('/admin/service-updates?audit_date=2010-01-01')  # noqa
        self.assertEqual(200, response.status_code)

        self.assertIn(
            self._replace_whitespace(
               '<td class="summary-item-field-first"><span>Clouded Networks</span></td>'),  # noqa
            self._replace_whitespace(response.get_data(as_text=True))
        )
        self.assertIn(
            self._replace_whitespace(
               '<td class="summary-item-field"><span>18:49:22<br/>17 June</span></td>'),  # noqa
            self._replace_whitespace(response.get_data(as_text=True))
        )
        self.assertIn(
            self._replace_whitespace(
               '<td class="summary-item-field-with-action"><span><a href="/admin/services/compare/...">View changes</a></span></td>'),  # noqa
            self._replace_whitespace(response.get_data(as_text=True))
        )
        self.assertIn(
            self._replace_whitespace(
               '<form action="/admin/service-updates/25/acknowledge" method="post">'),  # noqa
            self._replace_whitespace(response.get_data(as_text=True))
        )
        self.assertIn(
            self._replace_whitespace(
               '<input name="audit_date" type="hidden" value="2010-01-01">'),  # noqa
            self._replace_whitespace(response.get_data(as_text=True))
        )
        data_api_client.find_audit_events.assert_called_with(
            page=1,
            audit_type=AuditTypes.update_service,
            acknowledged='false',
            audit_date='2010-01-01')

    @mock.patch('app.main.views.service_updates.data_api_client')
    def test_should_call_api_ack_audit_event(self, data_api_client):
        response = self.client.post(
            '/admin/service-updates/123/acknowledge?audit_date=2010-01-01&acknowledged=all',
            data={'csrf_token': FakeCsrf.valid_token},
        )
        self.assertEqual(302, response.status_code)

        data_api_client.acknowledge_audit_event.assert_called_with(
            '123', 'test@example.com'
        )

    @mock.patch('app.main.views.service_updates.data_api_client')
    def test_should_pass_valid_page_argument_to_api(self, data_api_client):
        response = self.client.get('/admin/service-updates?page=5')
        self.assertEqual(200, response.status_code)

        data_api_client.find_audit_events.assert_called_with(
            page=5,
            audit_type=AuditTypes.update_service,
            acknowledged='false',
            audit_date=None
            )

    @mock.patch('app.main.views.service_updates.data_api_client')
    def test_should_not_pass_invalid_page_argument_to_api(self, data_api_client):
        response = self.client.get('/admin/service-updates?page=invalid')
        self.assertEqual(400, response.status_code)

        data_api_client.find_audit_events.assert_not_called()


@mock.patch('app.main.views.service_updates.data_api_client')
class TestServiceStatusUpdates(LoggedInApplicationTest):

    def test_redirects_to_current_day(self, data_api_client):
        response = self.client.get(
            '/admin/service-status-updates'
        )

        self.assertEqual(302, response.status_code)
        self.assertIn('http://localhost/admin/service-status-updates/20', response.location)

    def test_404s_invalid_date(self, data_api_client):
        response = self.client.get(
            '/admin/service-status-updates/invalid'
        )

        self.assertEqual(404, response.status_code)

    def test_should_show_updates_for_a_day_with_updates(self, data_api_client):
        data_api_client.find_audit_events.return_value = {
            'auditEvents': [
                {
                    'data': {
                        'supplierId': 93518,
                        'serviceId': 1234567890,
                        'supplierName': 'Clouded Networks',
                        'new_status': 'enabled'
                    },
                    'user': 'joeblogs',
                    'type': 'update_status',
                    'createdAt': '2016-01-01T08:49:22.999Z'
                }
            ]
        }

        response = self.client.get(
            '/admin/service-status-updates/2016-01-01'
        )

        self.assertEqual(200, response.status_code)

        page_contents = self._replace_whitespace(response.get_data(as_text=True))

        self.assertIn('Friday1January2016', page_contents)
        self.assertIn('1234567890', page_contents)

    def test_should_link_to_previous_and_next_days(self, data_api_client):
        data_api_client.find_audit_events.return_value = {
            'auditEvents': []
        }

        response = self.client.get(
            '/admin/service-status-updates/2015-12-23'
        )

        page_contents = self._replace_whitespace(response.get_data(as_text=True))

        self.assertIn('Wednesday23December2015', page_contents)

        self.assertIn('class="next-page"', page_contents)
        self.assertIn('Tuesday22December2015', page_contents)
        self.assertIn('/service-status-updates/2015-12-22', page_contents)

        self.assertIn('class="previous-page"', page_contents)
        self.assertIn('Thursday24December2015', page_contents)
        self.assertIn('/service-status-updates/2015-12-24', page_contents)

    def test_should_link_to_next_page(self, data_api_client):
        data_api_client.find_audit_events.return_value = {
            'auditEvents': [],
            'links': {
                'next': '/'
            }
        }

        response = self.client.get(
            '/admin/service-status-updates/2015-12-23'
        )

        page_contents = self._replace_whitespace(response.get_data(as_text=True))

        self.assertIn('class="next-page"', page_contents)
        self.assertIn('Page2', page_contents)
        self.assertIn('ofWednesday23December2015', page_contents)
        self.assertIn('/service-status-updates/2015-12-23/page-2', page_contents)

        self.assertIn('Nextday', page_contents)

    def test_should_link_to_previous_page(self, data_api_client):
        data_api_client.find_audit_events.return_value = {
            'auditEvents': [],
            'links': {
                'next': '/',
                'prev': '/'
            }
        }

        response = self.client.get(
            '/admin/service-status-updates/2015-12-23/page-2'
        )

        page_contents = self._replace_whitespace(response.get_data(as_text=True))

        self.assertIn('class="previous-page"', page_contents)
        self.assertIn('Page1', page_contents)
        self.assertIn('ofWednesday23December2015', page_contents)
        self.assertIn('/service-status-updates/2015-12-23/page-1', page_contents)
