import mock
from ...helpers import LoggedInApplicationTest
from lxml import html


@mock.patch('app.main.views.buyers.data_api_client')
class TestBuyersView(LoggedInApplicationTest):

    def test_should_be_a_404_if_no_brief_found(self, data_api_client):
        data_api_client.get_brief.return_value = None
        response = self.client.get('admin/buyers?brief_id=1')

        self.assertEqual(response.status_code, 404)

    def test_should_display_a_useful_message_if_no_brief_found(self, data_api_client):
        data_api_client.get_brief.return_value = None
        response = self.client.get('admin/buyers?brief_id=1')

        document = html.fromstring(response.get_data(as_text=True))
        banner_message = document.xpath('//p[@class="banner-message"]//text()')[0].strip()

        self.assertEqual("There are no opportunities with ID 1", banner_message)

    def test_brief_not_found_flash_message_injection(self, data_api_client):
        """
        Asserts that raw HTML in a bad brief ID cannot be injected into a flash message.
        """
        # impl copied from test_should_display_a_useful_message_if_no_brief_found
        data_api_client.get_brief.return_value = None
        response = self.client.get('admin/buyers?brief_id=1%3Cimg%20src%3Da%20onerror%3Dalert%281%29%3E')
        self.assertEqual(response.status_code, 404)

        html_response = response.get_data(as_text=True)
        self.assertNotIn("1<img src=a onerror=alert(1)>", html_response)
        self.assertIn("1&lt;img src=a onerror=alert(1)&gt;", html_response)

    def test_table_should_show_a_useful_message_if_no_users(self, data_api_client):
        data_api_client.get_brief.return_value = {
            'briefs': {
                'title': 'No users in here',
                'users': list()
            }
        }
        response = self.client.get('admin/buyers?brief_id=1')

        document = html.fromstring(response.get_data(as_text=True))
        table_content = document.xpath('//p[@class="summary-item-no-content"]//text()')[0].strip()

        self.assertEqual("No buyers to show", table_content)

    def test_should_show_buyers_contact_details(self, data_api_client):
        brief = self.load_example_listing("brief_response")
        data_api_client.get_brief.return_value = brief
        response = self.client.get('/admin/buyers?brief_id=1')

        document = html.fromstring(response.get_data(as_text=True))
        name = document.xpath('//td[@class="summary-item-field-first"]//text()')[1].strip()
        email = document.xpath('//td[@class="summary-item-field"]//text()')[1].strip()
        phone = document.xpath('//td[@class="summary-item-field"]//text()')[4].strip()

        self.assertEqual("Test Buyer", name)
        self.assertEqual("test_buyer@example.com", email)
        self.assertEqual("02078888888", phone)
