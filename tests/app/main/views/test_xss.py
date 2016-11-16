# coding=utf-8
from __future__ import unicode_literals

import mock
from ...helpers import LoggedInApplicationTest
from dmapiclient import HTTPError
import urllib


class TestXSS(LoggedInApplicationTest):
    @mock.patch('app.main.views.services.data_api_client')
    def test_service_not_found_flash_message_injection(self, data_api_client):
        """
        Asserts that raw HTML in a bad service ID cannot be injected into a flash message.
        """
        # impl copied from test_services.TestServiceView#test_redirect_with_flash_for_api_client_404
        api_response = mock.Mock()
        api_response.status_code = 404
        data_api_client.get_service.side_effect = HTTPError(api_response)

        evil_service_id = "1<img src=a onerror=alert(1)>"
        response1 = self.client.get('/admin/services/' + urllib.quote(evil_service_id))
        response2 = self.client.get(response1.location)
        self.assertNotIn(
            b'Error trying to retrieve service with ID: ' + evil_service_id.encode('utf8'),
            response2.data)

    @mock.patch('app.main.views.services.data_api_client')
    def test_brief_not_found_flash_message_injection(self, data_api_client):
        """
        Asserts that raw HTML in a bad brief ID cannot be injected into a flash message.
        """
        # impl copied from test_buyers.TestBuyersView#test_should_display_a_useful_message_if_no_brief_found
        data_api_client.get_brief.return_value = None
        evil_brief_id = "1<img src=a onerror=alert(1)>"
        response = self.client.get('admin/buyers?brief_id=' + urllib.quote(evil_brief_id))
        self.assertNotIn(
            b'There are no opportunities with ID ' + evil_brief_id.encode('utf8'),
            response.data)
