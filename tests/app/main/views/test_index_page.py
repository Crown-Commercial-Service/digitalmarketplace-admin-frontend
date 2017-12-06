import mock
import pytest

from ...helpers import LoggedInApplicationTest


class TestIndex(LoggedInApplicationTest):
    @mock.patch('app.main.views.services.data_api_client')
    def test_index_shows_frameworks_in_standstill_or_live(self, data_api_client):
        self.user_role = 'admin-ccs-sourcing'
        data_api_client.find_frameworks.return_value = {'frameworks': [
            {'id': 1, 'frameworkAgreementVersion': None, 'name': 'Framework 1', 'slug': 'framework-1',
             'status': 'standstill'},
            {'id': 2, 'frameworkAgreementVersion': 'v1.0', 'name': 'Framework 2', 'slug': 'framework-2',
             'status': 'live'},
            {'id': 3, 'frameworkAgreementVersion': None, 'name': 'Framework 3', 'slug': 'framework-3',
             'status': 'open'},
        ]}

        response = self.client.get('/admin')
        data = response.get_data(as_text=True)

        assert 'Download Framework 1 agreements' in data
        assert 'Approve Framework 2 agreements for countersigning' in data

        # Agreements should be in reverse-chronological order.
        assert (
            data.index('Approve Framework 2 agreements for countersigning') <
            data.index('Download Framework 1 agreements')
        )

        # Only standstill/live agreements should be listed.
        assert 'Download Framework 3 agreements' not in data

    @pytest.mark.parametrize("role, link_should_be_visible", [
        ("admin", True),
        ("admin-ccs-category", False),
        ("admin-ccs-sourcing", False),
        ("admin-framework-manager", False),
        ("admin-manager", False),
    ])
    def test_add_buyer_email_domain_link_is_shown_to_users_with_right_roles(self, role, link_should_be_visible):
        self.user_role = role
        response = self.client.get('/admin')
        data = response.get_data(as_text=True)
        link_is_visible = "Add a buyer email domain" in data

        assert link_is_visible is link_should_be_visible, (
            "Role {} {} see the link".format(role, "can not" if link_should_be_visible else "can")
        )

    @pytest.mark.parametrize("role, link_should_be_visible", [
        ("admin", True),
        ("admin-ccs-category", True),
        ("admin-ccs-sourcing", False),
        ("admin-framework-manager", False),
        ("admin-manager", False),
    ])
    def test_user_support_header_is_shown_to_users_with_right_roles(self, role, link_should_be_visible):
        self.user_role = role
        response = self.client.get('/admin')
        data = response.get_data(as_text=True)
        header_is_visible = "User support" in data

        assert header_is_visible is link_should_be_visible, (
            "Role {} {} see the link".format(role, "can not" if link_should_be_visible else "can")
        )

    @pytest.mark.parametrize("role, link_should_be_visible", [
        ("admin", True),
        ("admin-ccs-category", True),
        ("admin-ccs-sourcing", False),
        ("admin-framework-manager", False),
        ("admin-manager", False),
    ])
    def test_find_a_user_by_email_link_is_shown_to_users_with_right_roles(self, role, link_should_be_visible):
        self.user_role = role
        response = self.client.get('/admin')
        data = response.get_data(as_text=True)
        link_is_visible = "Find a user by email" in data

        assert link_is_visible is link_should_be_visible, (
            "Role {} {} see the link".format(role, "can not" if link_should_be_visible else "can")
        )

    @pytest.mark.parametrize("role, link_should_be_visible", [
        ("admin", False),
        ("admin-ccs-category", False),
        ("admin-ccs-sourcing", False),
        ("admin-framework-manager", False),
        ("admin-manager", True),
    ])
    def test_manage_admin_users_link_is_shown_to_users_with_the_right_role(self, role, link_should_be_visible):
        self.user_role = role
        response = self.client.get('/admin')
        data = response.get_data(as_text=True)
        link_is_visible = "Manage users" in data

        assert link_is_visible is link_should_be_visible, (
            "Role {} {} see the link".format(role, "can not" if link_should_be_visible else "can")
        )

    @pytest.mark.parametrize("role, link_should_be_visible", [
        ("admin", False),
        ("admin-ccs-category", True),
        ("admin-ccs-sourcing", False),
        ("admin-framework-manager", False),
        ("admin-manager", False),
    ])
    def test_check_service_edits_link_is_shown_to_users_with_the_right_role(self, role, link_should_be_visible):
        self.user_role = role
        response = self.client.get('/admin')
        data = response.get_data(as_text=True)
        link_is_visible = "Check edits to services" in data

        assert link_is_visible is link_should_be_visible, (
            "Role {} {} see the link".format(role, "can not" if link_should_be_visible else "can")
        )

    @pytest.mark.parametrize("role, link_should_be_visible", [
        ("admin", False),
        ("admin-ccs-category", False),
        ("admin-ccs-sourcing", True),
        ("admin-framework-manager", True),
        ("admin-manager", False),
    ])
    def test_statistics_link_is_shown_to_users_with_the_right_role(self, role, link_should_be_visible):
        self.user_role = role
        response = self.client.get('/admin')
        data = response.get_data(as_text=True)
        link_is_visible = "Statistics" in data

        assert link_is_visible is link_should_be_visible, (
            "Role {} {} see the link".format(role, "can not" if link_should_be_visible else "can")
        )

    @pytest.mark.parametrize("role, link_should_be_visible", [
        ("admin", False),
        ("admin-ccs-category", True),
        ("admin-ccs-sourcing", True),
        ("admin-framework-manager", True),
        ("admin-manager", False),
    ])
    def test_view_agreements_links_are_shown_to_users_with_the_right_role(self, role, link_should_be_visible):
        self.user_role = role
        response = self.client.get('/admin')
        data = response.get_data(as_text=True)
        link_is_visible = "Agreements" in data

        assert link_is_visible is link_should_be_visible, (
            "Role {} {} see the link".format(role, "can not" if link_should_be_visible else "can")
        )

    @pytest.mark.parametrize("role, link_should_be_visible", [
        ("admin", False),
        ("admin-ccs-category", False),
        ("admin-ccs-sourcing", False),
        ("admin-framework-manager", True),
        ("admin-manager", False),
    ])
    def test_view_communications_links_are_shown_to_users_with_the_right_role(self, role, link_should_be_visible):
        self.user_role = role
        response = self.client.get('/admin')
        data = response.get_data(as_text=True)
        link_is_visible = "Communications" in data

        assert link_is_visible is link_should_be_visible, (
            "Role {} {} see the link".format(role, "can not" if link_should_be_visible else "can")
        )

    @pytest.mark.parametrize("role, link_should_be_visible", [
        ("admin", False),
        ("admin-ccs-category", False),
        ("admin-ccs-sourcing", False),
        ("admin-framework-manager", True),
        ("admin-manager", False),
    ])
    def test_download_user_lists_link_is_shown_to_users_with_the_right_role(self, role, link_should_be_visible):
        self.user_role = role
        response = self.client.get('/admin')
        data = response.get_data(as_text=True)
        link_is_visible = "Download user lists" in data

        assert link_is_visible is link_should_be_visible, (
            "Role {} {} see the link".format(role, "can not" if link_should_be_visible else "can")
        )
