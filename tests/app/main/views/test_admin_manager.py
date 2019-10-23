from lxml import html
import mock
import pytest

from dmapiclient import HTTPError
from dmtestutils.mocking import assert_args_and_return

from ...helpers import LoggedInApplicationTest, Response


class TestAdminManagerListView(LoggedInApplicationTest):
    user_role = "admin-manager"

    SUPPORT_USERS = [
        {"active": True,
         "emailAddress": "support-1@example.com",
         "id": 9087,
         "name": "Rashguy Support",
         "role": "admin",
         },
        {"active": True,
         "emailAddress": "support-2@example.com",
         "id": 9088,
         "name": "Extra Support",
         "role": "admin",
         },
    ]
    CATEGORY_USERS = [
        {"active": True,
         "emailAddress": "category-support@example.com",
         "id": 9089,
         "name": "CCS Category Support",
         "role": "admin-ccs-category",
         },
        {"active": False,
         "emailAddress": "retired-category-support@example.com",
         "id": 9090,
         "name": "CCS Category Support - Retired",
         "role": "admin-ccs-category",
         },
    ]
    FRAMEWORK_MANAGER_USERS = [
        {"active": True,
         "emailAddress": "admin-framework-manager@example.com",
         "name": "Wonderful Framework Manager",
         "role": "admin-framework-manager",
         "id": 9093,
         },
        {"active": False,
         "emailAddress": "retired-admin-framework-manager@example.com",
         "name": "Has-been Framework Manager",
         "role": "admin-framework-manager",
         "id": 9094,
         },
    ]
    SOURCING_USERS = [
        {"active": False,
         "emailAddress": "old-sourcing-support@example.com",
         "id": 9091,
         "name": "Has-been Sourcing Support",
         "role": "admin-ccs-sourcing",
         },
        {"active": True,
         "emailAddress": "sourcing-support@example.com",
         "id": 9092,
         "name": "Sourcing Support",
         "role": "admin-ccs-sourcing",
         },
    ]
    DATA_CONTROLLER_USERS = [
        {"active": False,
         "emailAddress": "retired-admin-data-controller@example.com",
         "id": 9095,
         "name": "Suspended Admin Data Controller",
         "role": "admin-ccs-data-controller",
         },
        {"active": True,
         "emailAddress": "admin-data-controller@example.com",
         "id": 9096,
         "name": "Youthful Admin Data Controller",
         "role": "admin-ccs-data-controller",
         },
    ]

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.admin_manager.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    @pytest.mark.parametrize(
        "role_not_allowed",
        ["admin", "admin-ccs-category", "admin-ccs-sourcing", "admin-framework-manager", "admin-ccs-data-controller"]
    )
    def test_should_403_forbidden_user_roles(self, role_not_allowed):
        self.user_role = role_not_allowed
        response = self.client.get("/admin/admin-users")
        assert response.status_code == 403

    def test_should_raise_http_error_from_api(self):
        self.data_api_client.find_users_iter.side_effect = HTTPError(Response(404))
        response = self.client.get("/admin/admin-users")
        assert response.status_code == 404

    def test_should_list_admin_users(self):
        self.data_api_client.find_users_iter.side_effect = [
            iter(self.SUPPORT_USERS),
            iter(self.CATEGORY_USERS),
            iter(self.SOURCING_USERS),
            iter(self.FRAMEWORK_MANAGER_USERS),
            iter(self.DATA_CONTROLLER_USERS),
        ]
        response = self.client.get("/admin/admin-users")
        document = html.fromstring(response.get_data(as_text=True))

        assert response.status_code == 200
        assert len(document.cssselect(".summary-item-row")) == 10

    def test_should_list_alphabetically_with_all_suspended_users_below_active_users(self):
        self.data_api_client.find_users_iter.side_effect = [
            iter(self.SUPPORT_USERS),
            iter(self.CATEGORY_USERS),
            iter(self.SOURCING_USERS),
            iter(self.FRAMEWORK_MANAGER_USERS),
            iter(self.DATA_CONTROLLER_USERS),
        ]
        response = self.client.get("/admin/admin-users")
        document = html.fromstring(response.get_data(as_text=True))

        rows = document.cssselect(".summary-item-row")
        # Active users in alphabetical order (status, name, role)
        assert "Active" in rows[0].text_content()
        assert "Suspended" not in rows[0].text_content()
        assert "CCS Category Support" in rows[0].text_content()
        assert "Manage services" in rows[0].text_content()

        assert "Active" in rows[1].text_content()
        assert "Suspended" not in rows[1].text_content()
        assert "Extra Support" in rows[1].text_content()
        assert "Support accounts" in rows[1].text_content()

        assert "Active" in rows[2].text_content()
        assert "Suspended" not in rows[2].text_content()
        assert "Rashguy Support" in rows[2].text_content()
        assert "Support accounts" in rows[2].text_content()

        assert "Active" in rows[3].text_content()
        assert "Suspended" not in rows[3].text_content()
        assert "Sourcing Support" in rows[3].text_content()
        assert "Audit framework" in rows[3].text_content()

        assert "Active" in rows[4].text_content()
        assert "Suspended" not in rows[4].text_content()
        assert "Wonderful Framework Manager" in rows[4].text_content()
        assert "Manage framework" in rows[4].text_content()

        assert "Active" in rows[5].text_content()
        assert "Suspended" not in rows[5].text_content()
        assert "Youthful Admin Data Controller" in rows[5].text_content()
        assert "Manage data" in rows[5].text_content()

        # Deactivated users in alphabetical order (status, name, role)
        assert "Active" not in rows[6].text_content()
        assert "Suspended" in rows[6].text_content()
        assert "CCS Category Support - Retired" in rows[6].text_content()
        assert "Manage services" in rows[6].text_content()

        assert "Active" not in rows[7].text_content()
        assert "Suspended" in rows[7].text_content()
        assert "Has-been Framework Manager" in rows[7].text_content()
        assert "Manage framework" in rows[7].text_content()

        assert "Active" not in rows[8].text_content()
        assert "Suspended" in rows[8].text_content()
        assert "Has-been Sourcing Support" in rows[8].text_content()
        assert "Audit framework" in rows[8].text_content()

        assert "Active" not in rows[9].text_content()
        assert "Suspended" in rows[9].text_content()
        assert "Suspended Admin Data Controller" in rows[9].text_content()
        assert "Manage data" in rows[9].text_content()

    def test_should_link_to_edit_admin_user_page(self):
        self.data_api_client.find_users_iter.side_effect = [
            iter(self.SUPPORT_USERS),
            iter(self.CATEGORY_USERS),
            iter(self.SOURCING_USERS),
            iter(self.FRAMEWORK_MANAGER_USERS),
            iter(self.DATA_CONTROLLER_USERS),
        ]
        response = self.client.get("/admin/admin-users")
        document = html.fromstring(response.get_data(as_text=True))

        links = document.xpath("//td[@class='summary-item-field-with-action']//a/@href")

        assert links == [
            "/admin/admin-users/9089/edit",
            "/admin/admin-users/9088/edit",
            "/admin/admin-users/9087/edit",
            "/admin/admin-users/9092/edit",
            "/admin/admin-users/9093/edit",
            "/admin/admin-users/9096/edit",
            "/admin/admin-users/9090/edit",
            "/admin/admin-users/9094/edit",
            "/admin/admin-users/9091/edit",
            "/admin/admin-users/9095/edit",
        ]

    def test_should_have_invite_user_link(self):
        response = self.client.get("/admin/admin-users")
        document = html.fromstring(response.get_data(as_text=True))

        assert response.status_code == 200

        expected_link_text = "Invite user"
        expected_href = '/admin/admin-users/invite'
        expected_link = document.xpath('.//a[contains(@href,"{}")]'.format(expected_href))[0]

        assert expected_link.text == expected_link_text


class TestInviteAdminUserView(LoggedInApplicationTest):
    user_role = 'admin-manager'

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.forms.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    def get_validation_message(self, res):
        validation_message_xpath = '//span[@class="validation-message"]//text()'
        return html.fromstring(res.get_data(as_text=True)).xpath(validation_message_xpath)[0].strip()

    def test_get_with_correct_login_returns_200(self):
        res = self.client.get('/admin/admin-users/invite')
        assert res.status_code == 200

    @mock.patch('app.main.views.admin_manager.send_user_account_email')
    def test_post_requires_email(self, send_user_account_email):
        res = self.client.post('/admin/admin-users/invite', data={'role': 'admin'})

        assert res.status_code == 400
        assert self.get_validation_message(res) == "You must provide an email address"
        assert send_user_account_email.called is False

    @mock.patch('app.main.views.admin_manager.send_user_account_email')
    def test_post_requires_valid_email(self, send_user_account_email):
        res = self.client.post(
            '/admin/admin-users/invite',
            data={'role': 'admin', 'email_address': 'not_a_valid_email'}
        )
        assert res.status_code == 400
        assert self.get_validation_message(res) == "Please enter a valid email address"
        assert send_user_account_email.called is False

    @mock.patch('app.main.views.admin_manager.send_user_account_email')
    def test_post_requires_valid_admin_email(self, send_user_account_email):
        self.data_api_client.email_is_valid_for_admin_user.return_value = False
        res = self.client.post('/admin/admin-users/invite', data={'role': 'admin', 'email_address': 'test@test.com'})

        assert res.status_code == 400
        assert self.get_validation_message(res) == "The email address must belong to an approved domain"
        assert send_user_account_email.called is False

    @mock.patch('app.main.views.admin_manager.send_user_account_email')
    def test_email_address_with_existing_account_fails(self, send_user_account_email):
        self.data_api_client.get_user.return_value = {"users": {"emailAddress": "test@test.com"}}
        self.data_api_client.email_is_valid_for_admin_user.return_value = True
        res = self.client.post('/admin/admin-users/invite', data={'role': 'admin', 'email_address': 'test@test.com'})

        assert res.status_code == 400
        assert self.get_validation_message(res) == "This email address already has a user account associated with it"
        assert self.data_api_client.get_user.mock_calls == [mock.call(email_address="test@test.com")]
        send_user_account_email.called is False

    @mock.patch('app.main.views.admin_manager.send_user_account_email')
    def test_post_requires_role(self, send_user_account_email):
        self.data_api_client.get_user.side_effect = assert_args_and_return(None, email_address='test@test.com')
        res = self.client.post('/admin/admin-users/invite', data={'email_address': 'test@test.com'})
        assert res.status_code == 400
        assert self.get_validation_message(res) == "You must choose a permission"
        assert send_user_account_email.called is False

    @mock.patch('app.main.views.admin_manager.send_user_account_email')
    def test_post_requires_valid_role(self, send_user_account_email):
        """This case won't happen unless they mess with the post."""
        self.data_api_client.get_user.side_effect = assert_args_and_return(None, email_address='test@test.com')
        res = self.client.post(
            '/admin/admin-users/invite',
            data={'email_address': 'test@test.com', 'role': 'not_a_valid_role'}
        )
        assert res.status_code == 400
        assert self.get_validation_message(res) == "Not a valid choice"
        assert send_user_account_email.called is False

    @mock.patch('app.main.views.admin_manager.send_user_account_email')
    def test_successful_post_redirects(self, send_user_account_email):
        self.data_api_client.get_user.side_effect = assert_args_and_return(None, email_address='test@test.com')
        self.data_api_client.email_is_valid_for_admin_user.return_value = True
        res = self.client.post('/admin/admin-users/invite', data={'role': 'admin', 'email_address': 'test@test.com'})
        assert res.status_code == 302
        assert res.location == "http://localhost/admin/admin-users"
        assert send_user_account_email.called is True
        assert self.data_api_client.get_user.called is True

    @mock.patch('app.main.views.admin_manager.send_user_account_email')
    @pytest.mark.parametrize(
        'role',
        ('admin', 'admin-ccs-sourcing', 'admin-ccs-category', 'admin-framework-manager', 'admin-ccs-data-controller')
    )
    def test_post_is_successful_for_valid_roles(self, send_user_account_email, role):
        self.data_api_client.get_user.side_effect = assert_args_and_return(None, email_address='test@test.com')
        self.data_api_client.email_is_valid_for_admin_user.return_value = True
        res = self.client.post('/admin/admin-users/invite', data={'role': role, 'email_address': 'test@test.com'})
        assert res.status_code == 302
        assert send_user_account_email.called is True
        assert self.data_api_client.get_user.called is True

    @mock.patch('app.main.views.admin_manager.send_user_account_email')
    def test_successful_post_sends_email(self, send_user_account_email):
        self.data_api_client.get_user.side_effect = assert_args_and_return(None, email_address='test@test.com')
        self.data_api_client.email_is_valid_for_admin_user.return_value = True
        res = self.client.post('/admin/admin-users/invite', data={'role': 'admin', 'email_address': 'test@test.com'})

        assert res.status_code == 302
        send_user_account_email.assert_called_once_with(
            'admin',
            'test@test.com',
            '08ab7791-6038-4ad2-9560-740bbcb675b7',
            personalisation={'name': 'tester'}
        )
        assert self.data_api_client.get_user.called is True

    @mock.patch('app.main.views.admin_manager.send_user_account_email')
    def test_successful_post_flashes(self, send_user_account_email):
        self.data_api_client.get_user.side_effect = assert_args_and_return(None, email_address='test@test.com')
        self.data_api_client.email_is_valid_for_admin_user.return_value = True
        res = self.client.post('/admin/admin-users/invite', data={'role': 'admin', 'email_address': 'test@test.com'})
        assert res.status_code == 302
        self.assert_flashes('An invitation has been sent to test@test.com.')
        assert self.data_api_client.get_user.called is True


class TestAdminManagerEditsAdminUsers(LoggedInApplicationTest):
    user_role = "admin-manager"

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

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.admin_manager.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    def test_should_load_edit_admin_user_page_heading_and_submit_button_correctly(self):
        self.data_api_client.get_user.return_value = self.admin_user_to_edit

        response = self.client.get("/admin/admin-users/2345/edit")
        assert response.status_code == 200

        document = html.fromstring(response.get_data(as_text=True))

        user_email = "reality.auditor@digital.cabinet-office.gov.uk"
        assert document.cssselect('.govuk-heading-xl')[0].text.strip() == user_email
        assert document.cssselect('.govuk-main-wrapper .govuk-button')[0].text.strip() == "Update user"

    def test_edit_admin_user_form_prefills_edit_name_with_user_name(self):
        self.data_api_client.get_user.return_value = self.admin_user_to_edit

        response = self.client.get("/admin/admin-users/2345/edit")
        assert response.status_code == 200

        document = html.fromstring(response.get_data(as_text=True))

        assert document.xpath('//span[@class="question-heading"]')[0].text.strip() == "Name"
        assert document.cssselect('#input-edit_admin_name')[0].value == "Auditor of Reality"

    def test_edit_admin_user_form_prefills_permission_for_category_user(self):
        self.data_api_client.get_user.return_value = self.admin_user_to_edit

        response = self.client.get("/admin/admin-users/2345/edit")
        assert response.status_code == 200

        document = html.fromstring(response.get_data(as_text=True))

        assert document.xpath('//span[@class="question-heading"]')[1].text.strip() == "Permissions"

        permission_options_checked = [
            (input.label.text.strip(), input.checked)
            for input in document.xpath("//div[@id='edit_admin_permissions']//input")
        ]
        assert permission_options_checked == [
            ("Manage framework applications", False),
            ("Audit framework applications (CCS Sourcing)", False),
            ("Manage services (CCS Category)", True),
            ("Manage data (CCS Data Controller)", False),
            ("Support user accounts", False)
        ]
        permission_descriptions = [
            descr.strip() for descr in document.xpath("//p[@class='question-description']/text()")
        ]
        assert permission_descriptions == [
            'Manages communications about the framework and publishes supplier clarification questions.',
            'Checks declarations and agreements.',
            'Helps with service problems and makes sure services are in scope.',
            'Helps create consistent supplier data and updates company details.',
            'Helps buyers and suppliers solve problems with their accounts.'
        ]

    def test_edit_admin_user_form_prefills_status_with_active(self):
        self.data_api_client.get_user.return_value = self.admin_user_to_edit

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
        ("admin-ccs-data-controller", 403),
        ("admin-framework-manager", 403),
    ])
    def test_get_page_should_only_be_accessible_to_admin_manager(self, role, expected_code):
        self.user_role = role
        self.data_api_client.get_user.return_value = self.admin_user_to_edit

        response = self.client.get("/admin/admin-users/2345/edit")
        actual_code = response.status_code
        assert actual_code == expected_code, "Unexpected response {} for role {}".format(response.status_code, role)

    @pytest.mark.parametrize("role,expected_code", [
        ("admin-manager", 302),
        ("admin", 403),
        ("admin-ccs-category", 403),
        ("admin-ccs-sourcing", 403),
        ("admin-ccs-data-controller", 403),
        ("admin-framework-manager", 403),
    ])
    def test_post_page_should_only_be_accessible_to_admin_manager(self, role, expected_code):
        self.user_role = role
        self.data_api_client.get_user.return_value = self.admin_user_to_edit

        response = self.client.post(
            "/admin/admin-users/2345/edit",
            data={
                "edit_admin_name": "Lady Myria Lejean",
                "edit_admin_permissions": "admin",
                "edit_admin_status": "True"
            }
        )
        actual_code = response.status_code
        assert actual_code == expected_code, "Unexpected response {} for role {}".format(response.status_code, role)

    @pytest.mark.parametrize(
        'role',
        ['admin', 'admin-ccs-sourcing', 'admin-ccs-category', 'admin-framework-manager', "admin-ccs-data-controller"]
    )
    def test_admin_manager_can_edit_admin_user_details(self, role):
        self.data_api_client.get_user.return_value = self.admin_user_to_edit
        response1 = self.client.post(
            "/admin/admin-users/2345/edit",
            data={
                "edit_admin_name": "Lady Myria Lejean",
                "edit_admin_permissions": role,
                "edit_admin_status": "False"
            }
        )
        assert response1.status_code == 302
        self.assert_flashes("reality.auditor@digital.cabinet-office.gov.uk has been updated.", "message")
        assert self.data_api_client.update_user.call_args_list == [mock.call(
            "2345", name="Lady Myria Lejean", role=role, active=False
        )]

        assert response1.location == "http://localhost/admin/admin-users"
        response2 = self.client.get(response1.location)
        assert "reality.auditor@digital.cabinet-office.gov.uk has been updated." in response2.get_data(as_text=True)

    def test_admin_user_name_cannot_be_submitted_when_empty(self):
        self.data_api_client.get_user.return_value = self.admin_user_to_edit
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
        assert self.data_api_client.update_user.call_args_list == []

    def test_strip_whitespace_from_admin_user_name(self):
        self.user_role = "admin-manager"
        self.data_api_client.get_user.return_value = self.admin_user_to_edit
        self.client.post(
            "/admin/admin-users/2345/edit",
            data={
                "edit_admin_name": "Lady Myria Lejean    ",
                "edit_admin_permissions": "admin",
                "edit_admin_status": "True"
            }
        )
        self.data_api_client.update_user.assert_called_once()
        assert self.data_api_client.update_user.call_args[1]["name"] == "Lady Myria Lejean"

    def test_admin_user_active_to_bool(self):
        self.user_role = "admin-manager"
        self.data_api_client.get_user.return_value = self.admin_user_to_edit
        self.client.post(
            "/admin/admin-users/2345/edit",
            data={
                "edit_admin_name": "Lady Myria Lejean",
                "edit_admin_permissions": "admin",
                "edit_admin_status": "True"
            }
        )
        self.data_api_client.update_user.assert_called_once()
        assert self.data_api_client.update_user.call_args[1]["active"] is True
