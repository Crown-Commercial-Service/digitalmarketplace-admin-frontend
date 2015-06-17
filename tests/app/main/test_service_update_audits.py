import mock

from datetime import datetime

from ..helpers import LoggedInApplicationTest


class TestServiceUpdates(LoggedInApplicationTest):
    @mock.patch('app.main.service_update_audits.data_api_client')
    def test_should_render_activity_page_with_default_date(self, data_api_client):
        today = datetime.now().strftime("%d/%m/%Y")

        response = self.client.get('/admin/service-updates')
        self.assertEquals(200, response.status_code)

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


    @mock.patch('app.main.service_update_audits.data_api_client')
    def test_should_render_correct_form_defaults(self, data_api_client):
        response = self.client.get('/admin/service-updates')
        self.assertEquals(200, response.status_code)

        self.assertIn(
            '<input class="filter-field-text" id="audit_date" name="audit_date" type="text" value="">',  # noqa
            response.get_data(as_text=True)
        )

        self.assertIn(
            self._replace_whitespace(
                '<input name="acknowledged" value="all" id="acknowledged-1" type="radio" aria-controls="" checked>'),
            # noqa
            self._replace_whitespace(response.get_data(as_text=True))
        )

        data_api_client.find_audit_events.assert_called()


    @mock.patch('app.main.service_update_audits.data_api_client')
    def test_should_not_allow_invalid_dates(self, data_api_client):
        response = self.client.get('/admin/service-updates?audit_date=invalid')
        self.assertEquals(400, response.status_code)
        self.assertIn(
            "Not a valid date value",
            response.get_data(as_text=True)
        )
        self.assertIn(
            '<input class="filter-field-text" id="audit_date" name="audit_date" type="text" value="invalid">',  # noqa
            response.get_data(as_text=True)
        )

        self.assertIn(
            '<div class="validation-masthead" aria-labelledby="validation-masthead-heading">',  # noqa
            response.get_data(as_text=True)
        )

        self.assertIn(
            self._replace_whitespace(
                '<a href="#example-textbox" class="validation-masthead-link"><label for="audit_date">Audit Date</label></a>'),
            # noqa
            self._replace_whitespace(response.get_data(as_text=True))
        )

        data_api_client.find_audit_events.assert_not_called()


    @mock.patch('app.main.service_update_audits.data_api_client')
    def test_should_not_allow_invalid_acknowledges(self, data_api_client):
        response = self.client.get('/admin/service-updates?acknowledged=invalid')
        self.assertEquals(400, response.status_code)

        self.assertIn(
            self._replace_whitespace(
                '<a href="#example-textbox" class="validation-masthead-link"><label for="acknowledged">acknowledged</label></a>'),
            # noqa
            self._replace_whitespace(response.get_data(as_text=True))
        )
        data_api_client.find_audit_events.assert_not_called()

    @mock.patch('app.main.service_update_audits.data_api_client')
    def test_should_allow_valid_submission_with_all_fields(self, data_api_client):
        data_api_client.find_audit_events.return_value = {'auditEvents': []}

        response = self.client.get('/admin/service-updates?audit_date=2006-01-01&acknowledged=all')  # noqa
        self.assertEquals(200, response.status_code)
        self.assertIn(
            '<input class="filter-field-text" id="audit_date" name="audit_date" type="text" value="2006-01-01">',
            # noqa
            response.get_data(as_text=True)
        )

        self.assertIn(
            self._replace_whitespace(
                '<inputname="acknowledged"value="all"id="acknowledged-1"type="radio"aria-controls=""checked>'),  # noqa
            self._replace_whitespace(response.get_data(as_text=True))
        )
        data_api_client.find_audit_events.assert_called()

    @mock.patch('app.main.service_update_audits.data_api_client')
    def test_should_allow_valid_submission_with_only_date_fields(self, data_api_client):
        data_api_client.find_audit_events.return_value = {'auditEvents': []}

        response = self.client.get('/admin/service-updates?audit_date=2006-01-01')  # noqa
        self.assertEquals(200, response.status_code)
        self.assertIn(
            '<input class="filter-field-text" id="audit_date" name="audit_date" type="text" value="2006-01-01">',
            # noqa
            response.get_data(as_text=True)
        )

        self.assertIn(
            self._replace_whitespace(
                '<inputname="acknowledged"value="all"id="acknowledged-1"type="radio"aria-controls=""checked>'),  # noqa
            self._replace_whitespace(response.get_data(as_text=True))
        )
        data_api_client.find_audit_events.assert_called_with(
            audit_date='2006-01-01',
            audit_type='update_service',
            acknowledged='all')

    @mock.patch('app.main.service_update_audits.data_api_client')
    def test_should_allow_valid_submission_with_only_acknowledged_fields(self, data_api_client):
        data_api_client.find_audit_events.return_value = {'auditEvents': []}

        response = self.client.get('/admin/service-updates?acknowledged=not-acknowledged')  # noqa
        self.assertEquals(200, response.status_code)
        self.assertIn(
            '<input class="filter-field-text" id="audit_date" name="audit_date" type="text" value="">',
            # noqa
            response.get_data(as_text=True)
        )

        self.assertIn(
            self._replace_whitespace(
                '<inputname="acknowledged"value="not-acknowledged"id="acknowledged-3"type="radio"aria-controls=""checked>'),  # noqa
            self._replace_whitespace(response.get_data(as_text=True))
        )
        data_api_client.find_audit_events.assert_called_with(
            audit_date=None,
            audit_type='update_service',
            acknowledged='not-acknowledged')

    @mock.patch('app.main.service_update_audits.data_api_client')
    def test_should_call_api_with_correct_params(self, data_api_client):
        data_api_client.find_audit_events.return_value = {'auditEvents': []}

        response = self.client.get('/admin/service-updates?audit_date=2006-01-01&acknowledged=all')  # noqa
        self.assertEquals(200, response.status_code)

        data_api_client.find_audit_events.assert_called_with(
            audit_type='update_service',
            audit_date='2006-01-01',
            acknowledged='all')

    @mock.patch('app.main.service_update_audits.data_api_client')
    def test_should_call_api_with_none_date(self, data_api_client):
        data_api_client.find_audit_events.return_value = {'auditEvents': []}

        response = self.client.get('/admin/service-updates?acknowledged=all')  # noqa
        self.assertEquals(200, response.status_code)

        data_api_client.find_audit_events.assert_called_with(
            audit_type='update_service',
            audit_date=None,
            acknowledged='all')

    @mock.patch('app.main.service_update_audits.data_api_client')
    def test_should_render_activity_page_with_submitted_date(self, data_api_client):
        response = self.client.get('/admin/service-updates?audit_date=2010-01-01')

        self.assertEquals(200, response.status_code)

        date_header = """
        <p class="context">
            Activity for
        </p>
        <h1>
        01/01/2010
        </h1>
        """

        self.assertIn(
            self._replace_whitespace(date_header),
            self._replace_whitespace(response.get_data(as_text=True))
        )

        data_api_client.find_audit_events.assert_called()

    @mock.patch('app.main.service_update_audits.data_api_client')
    def test_should_redirect_to_update_page_with_correct_query_params(self, data_api_client):
        response = self.client.post(
            '/admin/service-updates/123/acknowledge',
            data={
                'acknowledged': 'all',
                'audit_date': '2010-01-05'
            }
        )

        self.assertEquals(302, response.status_code)
        self.assertEquals('http://localhost/admin/service-updates?acknowledged=all&audit_date=2010-01-05', response.location)
        data_api_client.acknowledge_audit_event.assert_called(
            audit_event_id=123,
            user='admin'
        )

    @mock.patch('app.main.service_update_audits.data_api_client')
    def test_should_not_call_api_when_form_errors(self, data_api_client):
        response = self.client.post(
            '/admin/service-updates/123/acknowledge',
            data={
                'acknowledged': 'not-acknowledged',
                'audit_date': 'invalid'
            }
        )

        self.assertEquals(400, response.status_code)
        data_api_client.acknowledge_audit_event.assert_not_called()
        self.assertIn(
            self._replace_whitespace(
                '<inputname="acknowledged"value="not-acknowledged"id="acknowledged-3"type="radio"aria-controls=""checked>'),  # noqa
            self._replace_whitespace(response.get_data(as_text=True))
        )
        self.assertIn(
            '<input class="filter-field-text" id="audit_date" name="audit_date" type="text" value="invalid">',
            # noqa
            response.get_data(as_text=True)
        )

    @mock.patch('app.main.service_update_audits.data_api_client')
    def test_should_show_no_updates_if_none_returned(self, data_api_client):
        data_api_client.find_audit_events.return_value = {'auditEvents': []}

        response = self.client.get('/admin/service-updates?audit_date=2006-01-01')  # noqa
        self.assertEquals(200, response.status_code)

        self.assertIn(
            self._replace_whitespace(
                'No events for this search'),  # noqa
            self._replace_whitespace(response.get_data(as_text=True))
        )
        data_api_client.find_audit_events.assert_called_with(
            audit_date='2006-01-01',
            audit_type='update_service',
            acknowledged='all')

    @mock.patch('app.main.service_update_audits.data_api_client')
    def test_should_show_no_updates_if_invalid_search(self, data_api_client):
        response = self.client.get('/admin/service-updates?audit_date=invalid')  # noqa
        self.assertEquals(400, response.status_code)

        self.assertIn(
            self._replace_whitespace(
                'No events for this search'),  # noqa
            self._replace_whitespace(response.get_data(as_text=True))
        )
        data_api_client.find_audit_events.assert_not_called()

    @mock.patch('app.main.service_update_audits.data_api_client')
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
                    'createdAt': '2015-06-17T08:49:22'
                }
            ],
            'links': {}
        }

        data_api_client.find_audit_events.return_value = audit_event
        response = self.client.get('/admin/service-updates?audit_date=2010-01-01')  # noqa
        self.assertEquals(200, response.status_code)

        self.assertIn(
            self._replace_whitespace(
               '<td class="summary-item-field-content">Clouded Networks</td>'),  # noqa
            self._replace_whitespace(response.get_data(as_text=True))
        )
        self.assertIn(
            self._replace_whitespace(
               '<td class="summary-item-field-content">08:49:22<br/>17/06/2015</td>'),  # noqa
            self._replace_whitespace(response.get_data(as_text=True))
        )
        self.assertIn(
            self._replace_whitespace(
               '<td class="summary-item-field-content"><a href="/admin/service-updates">View changes</a></td>'),  # noqa
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
            audit_type='update_service',
            acknowledged='all',
            audit_date='2010-01-01')

    @mock.patch('app.main.service_update_audits.data_api_client')
    def test_should_call_api_ack_audit_event(self, data_api_client):
        response = self.client.post('/admin/service-updates/123/acknowledge?audit_date=2010-01-01&acknowledged=all')  # noqa
        self.assertEquals(302, response.status_code)

        data_api_client.acknowledge_audit_event.assert_called_with('123', 'admin')
