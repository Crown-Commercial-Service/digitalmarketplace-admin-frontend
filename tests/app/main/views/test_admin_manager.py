import mock
import pytest
from lxml import html

from dmapiclient import HTTPError

from ...helpers import LoggedInApplicationTest, Response
from ..helpers.flash_tester import assert_flashes


@mock.patch("app.main.views.admin_manager.data_api_client")
class TestAdminManagerListView(LoggedInApplicationTest):

    SUPPORT_USERS = [
        {"active": True,
         "emailAddress": "support-1@example.com",
         "name": "Rashguy Support",
         "role": "admin",
         },
        {"active": True,
         "emailAddress": "support-2@example.com",
         "name": "Extra Support",
         "role": "admin",
         },
    ]
    CATEGORY_USERS = [
        {"active": True,
         "emailAddress": "category-support@example.com",
         "name": "CCS Category Support",
         "role": "admin-ccs-category",
         },
        {"active": False,
         "emailAddress": "retired-category-support@example.com",
         "name": "CCS Category Support - Retired",
         "role": "admin-ccs-category",
         },
    ]
    SOURCING_USERS = [
        {"active": False,
         "emailAddress": "old-sourcing-support@example.com",
         "name": "Has-been Sourcing Support",
         "role": "admin-ccs-sourcing",
         },
        {"active": True,
         "emailAddress": "sourcing-support@example.com",
         "name": "Sourcing Support",
         "role": "admin-ccs-sourcing",
         },
    ]

    @pytest.mark.parametrize("role_not_allowed", ["admin", "admin-ccs-category", "admin-ccs-sourcing"])
    def test_should_403_forbidden_user_roles(self, data_api_client, role_not_allowed):
        self.user_role = role_not_allowed
        response = self.client.get("/admin/admin-users")
        assert response.status_code == 403

    def test_should_raise_http_error_from_api(self, data_api_client):
        self.user_role = "admin-manager"
        data_api_client.find_users_iter.side_effect = HTTPError(Response(404))
        response = self.client.get("/admin/admin-users")
        assert response.status_code == 404

    def test_should_list_admin_users(self, data_api_client):
        self.user_role = "admin-manager"
        data_api_client.find_users_iter.side_effect = [
            iter(self.SUPPORT_USERS),
            iter(self.CATEGORY_USERS),
            iter(self.SOURCING_USERS)
        ]
        response = self.client.get("/admin/admin-users")
        document = html.fromstring(response.get_data(as_text=True))

        assert response.status_code == 200
        assert len(document.cssselect(".summary-item-row")) == 6

    def test_should_list_alphabetically_with_all_suspended_users_below_active_users(self, data_api_client):
        self.user_role = "admin-manager"
        data_api_client.find_users_iter.side_effect = [
            iter(self.SUPPORT_USERS),
            iter(self.CATEGORY_USERS),
            iter(self.SOURCING_USERS)
        ]
        response = self.client.get("/admin/admin-users")
        document = html.fromstring(response.get_data(as_text=True))

        rows = document.cssselect(".summary-item-row")
        # Active users in alphabetical order
        assert "Active" in rows[0].text_content()
        assert "Suspended" not in rows[0].text_content()
        assert "CCS Category Support" in rows[0].text_content()

        assert "Active" in rows[1].text_content()
        assert "Suspended" not in rows[1].text_content()
        assert "Extra Support" in rows[1].text_content()

        assert "Active" in rows[2].text_content()
        assert "Suspended" not in rows[2].text_content()
        assert "Rashguy Support" in rows[2].text_content()

        assert "Active" in rows[3].text_content()
        assert "Suspended" not in rows[3].text_content()
        assert "Sourcing Support" in rows[3].text_content()

        # Deactivated users in alphabetical order
        assert "Active" not in rows[4].text_content()
        assert "Suspended" in rows[4].text_content()
        assert "CCS Category Support - Retired" in rows[4].text_content()

        assert "Active" not in rows[5].text_content()
        assert "Suspended" in rows[5].text_content()
        assert "Has-been Sourcing Support" in rows[5].text_content()


@mock.patch('app.main.forms.data_api_client', autospec=True)
class TestInviteAdminUserView(LoggedInApplicationTest):
    user_role = 'admin-manager'

    def get_validation_message(self, res):
        validation_message_xpath = '//span[@class="validation-message"]//text()'
        return html.fromstring(res.get_data(as_text=True)).xpath(validation_message_xpath)[0].strip()

    def test_get_with_correct_login_returns_200(self, data_api_client):
        res = self.client.get('/admin/admin-users/invite')
        assert res.status_code == 200

    def test_post_requires_email(self, data_api_client):
        res = self.client.post('/admin/admin-users/invite', data={'role': 'admin'})

        assert res.status_code == 400
        assert self.get_validation_message(res) == "You must provide an email address"

    def test_post_requires_valid_email(self, data_api_client):
        res = self.client.post(
            '/admin/admin-users/invite',
            data={'role': 'admin', 'email_address': 'not_a_valid_email'}
        )
        assert res.status_code == 400
        assert self.get_validation_message(res) == "Please enter a valid email address"

    def test_post_requires_valid_admin_email(self, data_api_client):
        data_api_client.email_is_valid_for_admin_user.return_value = False
        res = self.client.post('/admin/admin-users/invite', data={'role': 'admin', 'email_address': 'test@test.com'})

        assert res.status_code == 400
        assert self.get_validation_message(res) == "The email address must belong to an approved domain"

    def test_post_requires_role(self, data_api_client):
        res = self.client.post('/admin/admin-users/invite', data={'email_address': 'test@test.com'})
        assert res.status_code == 400
        assert self.get_validation_message(res) == "You must choose a permission"

    def test_post_requires_valid_role(self, data_api_client):
        """This case won't happen unless they mess with the post."""
        res = self.client.post(
            '/admin/admin-users/invite',
            data={'email_address': 'test@test.com', 'role': 'not_a_valid_role'}
        )
        assert res.status_code == 400
        assert self.get_validation_message(res) == "Not a valid choice"

    @mock.patch('app.main.views.admin_manager.send_user_account_email')
    def test_successful_post_redirects(self, send_user_account_email, data_api_client):
        data_api_client.email_is_valid_for_admin_user.return_value = True
        res = self.client.post('/admin/admin-users/invite', data={'role': 'admin', 'email_address': 'test@test.com'})
        assert res.status_code == 302
        assert res.location == "http://localhost/admin/admin-users"

    @mock.patch('app.main.views.admin_manager.send_user_account_email')
    @pytest.mark.parametrize('role', ('admin', 'admin-ccs-sourcing', 'admin-ccs-category'))
    def test_post_is_successful_for_valid_roles(self, send_user_account_email, data_api_client, role):
        data_api_client.email_is_valid_for_admin_user.return_value = True
        res = self.client.post('/admin/admin-users/invite', data={'role': role, 'email_address': 'test@test.com'})
        assert res.status_code == 302

    @mock.patch('app.main.views.admin_manager.send_user_account_email')
    def test_successful_post_sends_email(self, send_user_account_email, data_api_client):
        data_api_client.email_is_valid_for_admin_user.return_value = True
        res = self.client.post('/admin/admin-users/invite', data={'role': 'admin', 'email_address': 'test@test.com'})

        assert res.status_code == 302
        send_user_account_email.assert_called_once_with(
            'admin',
            'test@test.com',
            '08ab7791-6038-4ad2-9560-740bbcb675b7',
            personalisation={'name': 'tester'}
        )

    @mock.patch('app.main.views.admin_manager.send_user_account_email')
    def test_successful_post_flashes(self, data_api_client, send_user_account_email):
        data_api_client.email_is_valid_for_admin_user.return_value = True
        res = self.client.post('/admin/admin-users/invite', data={'role': 'admin', 'email_address': 'test@test.com'})
        assert res.status_code == 302
        assert_flashes(self, 'An invitation has been sent to test@test.com.', 'success')
