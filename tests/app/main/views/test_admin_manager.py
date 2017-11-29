from __future__ import unicode_literals
from lxml import html
import mock
import pytest

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

    def test_should_have_invite_user_link(self, data_api_client):
        self.user_role = "admin-manager"
        response = self.client.get("/admin/admin-users")
        document = html.fromstring(response.get_data(as_text=True))

        assert response.status_code == 200

        expected_link_text = "Invite user"
        expected_href = '/admin/admin-users/invite'
        expected_link = document.xpath('.//a[contains(@href,"{}")]'.format(expected_href))[0]

        assert expected_link.text == expected_link_text


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


@mock.patch("app.main.views.admin_manager.data_api_client")
class TestAdminManagerEditsAdminUsers(LoggedInApplicationTest):

    admin_user_to_edit = {
        "users": {
            "active": True,
            "emailAddress": "reality.auditor@digital.cabinet-office.gov.uk",
            "id": 2345,
            "locked": False,
            "name": "Auditor of Reality",
            "role": "admin-ccs-category",
            "updatedAt": "2017-11-22T14:42:27.043468Z"
        }
    }

    def test_should_load_edit_admin_users_page_heading_correctly(self, data_api_client):
        self.user_role = "admin-manager"
        data_api_client.get_user.return_value = self.admin_user_to_edit

        response = self.client.get("/admin/admin-users/2345/edit")
        assert response.status_code == 200

        document = html.fromstring(response.get_data(as_text=True))

        assert document.xpath('//h1')[0].text.strip() == "reality.auditor@digital.cabinet-office.gov.uk"
        assert document.xpath('//input[@class="button-save"]')[0].value.strip() == "Update user"

    def test_should_correctly_load_and_prefill_edit_name_question(self, data_api_client):
        self.user_role = "admin-manager"
        data_api_client.get_user.return_value = self.admin_user_to_edit

        response = self.client.get("/admin/admin-users/2345/edit")
        assert response.status_code == 200

        document = html.fromstring(response.get_data(as_text=True))

        assert document.xpath('//span[@class="question-heading"]')[0].text.strip() == "Name"
        assert document.cssselect('#input-edit_admin_name')[0].value == "Auditor of Reality"

    def test_should_correctly_load_and_prefill_edit_permissions_question(self, data_api_client):
        self.user_role = "admin-manager"
        data_api_client.get_user.return_value = self.admin_user_to_edit

        response = self.client.get("/admin/admin-users/2345/edit")
        assert response.status_code == 200

        document = html.fromstring(response.get_data(as_text=True))

        assert document.xpath('//span[@class="question-heading"]')[1].text.strip() == "Permissions"

        assert document.cssselect('#input-edit_admin_permissions-1')[0].label.text.strip() == "Category"
        assert document.cssselect('#input-edit_admin_permissions-1')[0].checked

        assert document.cssselect('#input-edit_admin_permissions-2')[0].label.text.strip() == "Sourcing"
        assert not document.cssselect('#input-edit_admin_permissions-2')[0].checked

        assert document.cssselect('#input-edit_admin_permissions-3')[0].label.text.strip() == "Support"
        assert not document.cssselect('#input-edit_admin_permissions-3')[0].checked

    def test_should_correctly_load_and_prefill_edit_status_question(self, data_api_client):
        self.user_role = "admin-manager"
        data_api_client.get_user.return_value = self.admin_user_to_edit

        response = self.client.get("/admin/admin-users/2345/edit")
        assert response.status_code == 200

        document = html.fromstring(response.get_data(as_text=True))

        assert document.xpath('//span[@class="question-heading"]')[2].text.strip() == "Status"

        assert document.cssselect('#input-edit_admin_status-1')[0].label.text.strip() == "Active"
        assert document.cssselect('#input-edit_admin_status-1')[0].checked

        assert document.cssselect('#input-edit_admin_status-2')[0].label.text.strip() == "Suspended"
        assert not document.cssselect('#input-edit_admin_status-2')[0].checked

    @pytest.mark.parametrize("role,expected_code", [
        ("admin-manager", 200),
        ("admin", 403),
        ("admin-ccs-category", 403),
        ("admin-ccs-sourcing", 403),
    ])
    def test_get_page_should_only_be_accessible_to_admin_manager(self, data_api_client, role, expected_code):
        self.user_role = role
        data_api_client.get_user.return_value = self.admin_user_to_edit

        response = self.client.get("/admin/admin-users/2345/edit")
        actual_code = response.status_code
        assert actual_code == expected_code, "Unexpected response {} for role {}".format(response.status_code, role)

    @pytest.mark.parametrize("role,expected_code", [
        ("admin-manager", 302),
        ("admin", 403),
        ("admin-ccs-category", 403),
        ("admin-ccs-sourcing", 403),
    ])
    def test_post_page_should_only_be_accessible_to_admin_manager(self, data_api_client, role, expected_code):
        self.user_role = role
        data_api_client.get_user.return_value = self.admin_user_to_edit

        response = self.client.post('/admin/admin-users/2345/edit')
        actual_code = response.status_code
        assert actual_code == expected_code, "Unexpected response {} for role {}".format(response.status_code, role)

    def test_admin_manager_can_edit_admin_user_details(self, data_api_client):
        self.user_role = "admin-manager"
        data_api_client.get_user.return_value = self.admin_user_to_edit
        response1 = self.client.post(
            "/admin/admin-users/2345/edit",
            data={
                "edit_admin_name": "Lady Myria Lejean",
                "edit_admin_permissions": "admin",
                "edit_admin_status": "False"
            }
        )
        assert response1.status_code == 302
        assert_flashes(self, "reality.auditor@digital.cabinet-office.gov.uk has been updated", "message")
        assert data_api_client.update_user.call_args_list == [mock.call(
            "2345", name="Lady Myria Lejean", role="admin", active=False
        )]

        response2 = self.client.get(response1.location)
        assert "reality.auditor@digital.cabinet-office.gov.uk has been updated" in response2.get_data(as_text=True)

    def test_admin_user_name_cannot_be_submitted_when_empty(self, data_api_client):
        self.user_role = "admin-manager"
        data_api_client.get_user.return_value = self.admin_user_to_edit
        response = self.client.post(
            "/admin/admin-users/2345/edit",
            data={
                "edit_admin_name": "",
                "edit_admin_permissions": "admin",
                "edit_admin_status": "True"
            }
        )
        assert response.status_code == 400
        assert "You must provide a name." in response.get_data(as_text=True)
        assert data_api_client.update_user.call_args_list == []
