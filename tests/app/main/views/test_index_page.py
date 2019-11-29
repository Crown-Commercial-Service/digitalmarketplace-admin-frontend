import mock
import pytest
from lxml import html
from dmtestutils.api_model_stubs import FrameworkStub

from ...helpers import LoggedInApplicationTest


class TestIndex(LoggedInApplicationTest):

    @pytest.mark.parametrize("role", [
        "admin",
        "admin-ccs-category",
        "admin-ccs-sourcing",
        "admin-framework-manager",
        "admin-manager",
        "admin-ccs-data-controller",
    ])
    def test_change_password_link_is_shown_to_all_admin_users(self, role):
        self.user_role = role
        response = self.client.get('/admin')
        assert response.status_code == 200
        document = html.fromstring(response.get_data(as_text=True))
        assert bool(document.xpath('.//a[@href="/user/change-password"]')), "Role {} cannot see the link".format(role)

    @pytest.mark.parametrize("role, link_should_be_visible", [
        ("admin", True),
        ("admin-ccs-category", True),
        ("admin-ccs-sourcing", False),
        ("admin-framework-manager", False),
        ("admin-manager", False),
        ("admin-ccs-data-controller", False),
    ])
    def test_add_buyer_email_domain_link_is_shown_to_users_with_right_roles(self, role, link_should_be_visible):
        self.user_role = role
        response = self.client.get('/admin')
        assert response.status_code == 200
        document = html.fromstring(response.get_data(as_text=True))
        link_is_visible = bool(document.xpath('.//a[@href="/admin/buyers/add-buyer-domains"]'))

        assert link_is_visible is link_should_be_visible, (
            "Role {} {} see the link".format(role, "cannot" if link_should_be_visible else "can")
        )

    @pytest.mark.parametrize("role, header_should_be_visible", [
        ("admin", True),
        ("admin-ccs-category", True),
        ("admin-ccs-sourcing", True),
        ("admin-framework-manager", True),
        ("admin-manager", False),
        ("admin-ccs-data-controller", False),
    ])
    def test_user_support_header_is_shown_to_users_with_right_roles(self, role, header_should_be_visible):
        self.user_role = role
        response = self.client.get('/admin')
        assert response.status_code == 200
        document = html.fromstring(response.get_data(as_text=True))
        header_is_visible = bool(document.xpath('.//h2[contains(text(),"User support")]'))

        assert header_is_visible is header_should_be_visible, (
            "Role {} {} see the header".format(role, "cannot" if header_should_be_visible else "can")
        )

    @pytest.mark.parametrize("role, link_should_be_visible", [
        ("admin", True),
        ("admin-ccs-category", True),
        ("admin-ccs-sourcing", False),
        ("admin-framework-manager", False),
        ("admin-manager", False),
        ("admin-ccs-data-controller", True),
    ])
    def test_find_a_user_by_email_link_is_shown_to_users_with_right_roles(self, role, link_should_be_visible):
        self.user_role = role
        response = self.client.get('/admin')
        assert response.status_code == 200
        document = html.fromstring(response.get_data(as_text=True))
        link_is_visible = bool(document.xpath('.//a[@href="/admin/users"]'))

        assert link_is_visible is link_should_be_visible, (
            "Role {} {} see the link".format(role, "cannot" if link_should_be_visible else "can")
        )

    @pytest.mark.parametrize("role, link_should_be_visible", [
        ("admin", False),
        ("admin-ccs-category", False),
        ("admin-ccs-sourcing", False),
        ("admin-framework-manager", False),
        ("admin-manager", True),
        ("admin-ccs-data-controller", False),
    ])
    def test_manage_admin_users_link_is_shown_to_users_with_the_right_role(self, role, link_should_be_visible):
        self.user_role = role
        response = self.client.get('/admin')
        assert response.status_code == 200
        document = html.fromstring(response.get_data(as_text=True))
        link_is_visible = bool(document.xpath('.//a[@href="/admin/admin-users"]'))

        assert link_is_visible is link_should_be_visible, (
            "Role {} {} see the link".format(role, "cannot" if link_should_be_visible else "can")
        )

    @pytest.mark.parametrize("role, link_should_be_visible", [
        ("admin", False),
        ("admin-ccs-category", True),
        ("admin-ccs-sourcing", False),
        ("admin-framework-manager", False),
        ("admin-manager", False),
        ("admin-ccs-data-controller", False),
    ])
    def test_check_service_edits_link_is_shown_to_users_with_the_right_role(self, role, link_should_be_visible):
        self.user_role = role
        response = self.client.get('/admin')
        assert response.status_code == 200
        document = html.fromstring(response.get_data(as_text=True))
        link_is_visible = bool(document.xpath('.//a[@href="/admin/services/updates/unapproved"]'))

        assert link_is_visible is link_should_be_visible, (
            "Role {} {} see the link".format(role, "cannot" if link_should_be_visible else "can")
        )

    @pytest.mark.parametrize("role, header_should_be_visible", [
        ("admin", False),
        ("admin-ccs-category", True),
        ("admin-ccs-sourcing", True),
        ("admin-framework-manager", True),
        ("admin-manager", False),
        ("admin-ccs-data-controller", False),
    ])
    def test_manage_applications_header_is_shown_to_users_with_the_right_role(self, role, header_should_be_visible):
        self.user_role = role
        response = self.client.get('/admin')
        assert response.status_code == 200
        document = html.fromstring(response.get_data(as_text=True))
        header_is_visible = bool(document.xpath('.//h2[contains(text(),"Manage applications")]'))

        assert header_is_visible is header_should_be_visible, (
            "Role {} {} see the header".format(role, "cannot" if header_should_be_visible else "can")
        )

    @pytest.mark.parametrize("role, link_should_be_visible", [
        ("admin", True),
        ("admin-ccs-category", True),
        ("admin-ccs-sourcing", False),
        ("admin-framework-manager", False),
        ("admin-manager", False),
        ("admin-ccs-data-controller", False),
    ])
    def test_find_buyer_by_opportunity_id_link_is_shown_to_users_with_right_roles(self, role, link_should_be_visible):
        self.user_role = role
        response = self.client.get('/admin')
        assert response.status_code == 200
        document = html.fromstring(response.get_data(as_text=True))
        link_is_visible = bool(document.xpath('.//a[@href="/admin/buyers"]'))

        assert link_is_visible is link_should_be_visible, (
            "Role {} {} see the link".format(role, "cannot" if link_should_be_visible else "can")
        )

    @pytest.mark.parametrize("role, link_should_be_visible, expected_link_text", [
        ("admin", True, 'Edit supplier accounts or view services'),
        ("admin-ccs-category", True, 'Edit suppliers and services'),
        ("admin-ccs-sourcing", True, 'Edit supplier declarations'),
        ("admin-framework-manager", True, 'View suppliers and services'),
        ("admin-manager", False, None),
        ("admin-ccs-data-controller", True, "View and edit suppliers"),
    ])
    def test_link_to_search_suppliers_and_services_page_is_shown_with_role_dependent_text(
            self, role, link_should_be_visible, expected_link_text
    ):
        self.user_role = role
        response = self.client.get('/admin')
        assert response.status_code == 200
        document = html.fromstring(response.get_data(as_text=True))
        link_is_visible = bool(document.xpath('.//a[@href="/admin/search"]'))

        assert link_is_visible is link_should_be_visible, (
            "Role {} {} see the link".format(role, "cannot" if link_should_be_visible else "can")
        )
        if link_should_be_visible:
            link_text = document.xpath('.//a[@href="/admin/search"]//text()')[0].strip()
            assert link_text == expected_link_text

    @pytest.mark.parametrize("link_url, expected_link_text", [
        ("/admin/users/download/buyers", "Download list of all buyers"),
        ("/admin/users/download/buyers/user-research", "Download potential user research participants (buyers)"),
        ("/admin/users/download/suppliers", "Download potential user research participants (suppliers)"),
    ])
    @pytest.mark.parametrize("role, link_should_be_visible", [
        ("admin", False),
        ("admin-ccs-category", False),
        ("admin-ccs-sourcing", False),
        ("admin-framework-manager", True),
        ("admin-manager", False),
        ("admin-ccs-data-controller", False),
    ])
    def test_links_to_download_buyer_and_user_research_lists_are_shown_with_role_dependent_text(
        self, role, link_should_be_visible, link_url, expected_link_text
    ):
        self.user_role = role
        response = self.client.get('/admin')
        assert response.status_code == 200
        document = html.fromstring(response.get_data(as_text=True))
        link_is_visible = bool(document.xpath('.//a[@href="{}"]'.format(link_url)))

        assert link_is_visible is link_should_be_visible, (
            "Role {} {} see the link".format(role, "cannot" if link_should_be_visible else "can")
        )
        if link_should_be_visible:
            link_text = document.xpath('.//a[@href="{}"]//text()'.format(link_url))[0].strip()
            assert link_text == expected_link_text


class TestFrameworkActionsOnIndexPage(LoggedInApplicationTest):

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.services.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()
        self.data_api_client.find_frameworks.return_value = self._get_frameworks_list_fixture_data()
        self.pp_id_mapping_patch = mock.patch.dict(
            self.app.config["PERFORMANCE_PLATFORM_ID_MAPPING"],
            {"amazing-digital-framework": "amazing-digitalized-framework"},
        )
        self.pp_id_mapping_patch.start()

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        self.pp_id_mapping_patch.stop()
        super().teardown_method(method)

    @staticmethod
    def _get_mock_framework_response(framework_status):
        return {"frameworks": [
            {
                "id": 1,
                "name": "Amazing Digital Framework",
                "slug": "amazing-digital-framework",
                "family": "amazing-digital-framework",
                "status": framework_status,
            },

        ]}

    @pytest.mark.parametrize('framework_status, header_shown', [
        ('coming', False),
        ('open', True),
        ('pending', True),
        ('standstill', True),
        ('live', True),
        ('expired', False),
    ])
    def test_framework_action_lists_not_shown_for_expired_frameworks(
        self, framework_status, header_shown
    ):
        self.data_api_client.find_frameworks.return_value = self._get_mock_framework_response(framework_status)

        self.user_role = "admin-framework-manager"
        response = self.client.get('/admin')
        assert response.status_code == 200
        document = html.fromstring(response.get_data(as_text=True))

        assert bool(document.xpath('.//h3[contains(text(),"Amazing Digital Framework")]')) == header_shown

    @pytest.mark.parametrize('family,should_be_shown', (
        ('g-cloud', False),
        ('digital-outcomes-and-specialists', True),
    ))
    def test_dos_only_expired_framework_action_lists_shown_for(self, family, should_be_shown):
        self.data_api_client.find_frameworks.return_value = {'frameworks': [FrameworkStub(
            status='expired',
            slug=f'flim-flam-3',
            family=family,
            name=f'Flim Flam Framework 3',
        ).response()]}

        self.user_role = "admin-framework-manager"
        response = self.client.get('/admin')
        assert response.status_code == 200
        document = html.fromstring(response.get_data(as_text=True))

        assert bool(
            document.xpath(f'.//h3[contains(text(),"Flim Flam Framework 3")]')
        ) == should_be_shown

    @pytest.mark.parametrize('framework_status, header_shown', [
        ('coming', False),
        ('open', False),
        ('pending', False),
        ('standstill', True),
        ('live', True),
        ('expired', False),
    ])
    def test_framework_action_lists_only_shown_when_framework_standstill_or_live_for_category_users(
        self, framework_status, header_shown
    ):
        self.data_api_client.find_frameworks.return_value = self._get_mock_framework_response(framework_status)

        self.user_role = "admin-ccs-category"
        response = self.client.get('/admin')
        assert response.status_code == 200
        document = html.fromstring(response.get_data(as_text=True))

        assert bool(document.xpath('.//h3[contains(text(),"Amazing Digital Framework")]')) == header_shown

    @pytest.mark.parametrize('framework_status, agreements_shown, stats_shown, comms_shown, contact_shown', [
        ('coming', False, False, False, False),
        ('open', False, True, True, True),
        ('pending', False, True, True, True),
        ('standstill', True, True, True, True),
        ('live', True, True, True, True),
        ('expired', False, False, False, False),
    ])
    def test_framework_action_lists_only_contain_actions_for_framework_status(
        self, framework_status, agreements_shown, stats_shown, comms_shown, contact_shown
    ):
        self.data_api_client.find_frameworks.return_value = self._get_mock_framework_response(framework_status)
        self.user_role = "admin-framework-manager"
        response = self.client.get('/admin')
        assert response.status_code == 200
        document = html.fromstring(response.get_data(as_text=True))

        assert bool(document.xpath('.//a[contains(text(),"agreements")]')) == agreements_shown
        assert bool(document.xpath('.//a[contains(text(),"View application statistics")]')) == stats_shown
        assert bool(document.xpath('.//a[contains(text(),"Manage communications")]')) == comms_shown
        assert bool(document.xpath('.//a[contains(text(),"Contact suppliers")]')) == contact_shown

    def test_stats_link_not_shown_if_no_pp_id(self):
        self.data_api_client.find_frameworks.return_value = {"frameworks": [
            {
                "id": 7,
                "name": "Mediocre Digital Framework",
                "slug": "mediocre-digital-framework",
                "family": "mediocre-digital-framework",
                "status": "open",
            },

        ]}
        self.user_role = "admin-framework-manager"
        response = self.client.get('/admin')
        document = html.fromstring(response.get_data(as_text=True))

        assert not document.xpath('.//a[contains(text(),"View application statistics")]')

    @pytest.mark.parametrize("role, link_should_be_visible, expected_link_text", [
        ("admin", False, None),
        ("admin-ccs-category", True, "View agreements"),
        ("admin-ccs-sourcing", True, "Countersign agreements"),
        ("admin-framework-manager", True, "View agreements"),
        ("admin-manager", False, None),
        ("admin-ccs-data-controller", False, None),
    ])
    def test_framework_action_list_includes_agreements_link(self, role, link_should_be_visible, expected_link_text):
        self.user_role = role
        response = self.client.get('/admin')
        assert response.status_code == 200
        document = html.fromstring(response.get_data(as_text=True))
        link_is_visible = bool(document.xpath('.//a[contains(text(),"agreements")]'))

        assert link_is_visible is link_should_be_visible, (
            "Role {} {} see the link".format(role, "can not" if link_should_be_visible else "can")
        )
        if expected_link_text:
            link_text = document.xpath('.//a[contains(text(),"agreements")]//text()')[0].strip()
            assert link_text == expected_link_text, (
                "Agreements link text for role {} is {}".format(role, expected_link_text)
            )

    @pytest.mark.parametrize("role, link_should_be_visible", [
        ("admin", False),
        ("admin-ccs-category", True),
        ("admin-ccs-sourcing", False),
        ("admin-framework-manager", True),
        ("admin-manager", False),
        ("admin-ccs-data-controller", False),
    ])
    def test_framework_action_list_includes_contact_suppliers(self, role, link_should_be_visible):
        self.user_role = role
        response = self.client.get('/admin')
        assert response.status_code == 200
        document = html.fromstring(response.get_data(as_text=True))
        link_is_visible = bool(document.xpath('.//a[contains(text(),"Contact suppliers")]'))

        assert link_is_visible is link_should_be_visible, (
            "Role {} {} see the link".format(role, "cannot" if link_should_be_visible else "can")
        )

    @pytest.mark.parametrize("role, link_should_be_visible", [
        ("admin", False),
        ("admin-ccs-category", False),
        ("admin-ccs-sourcing", False),
        ("admin-framework-manager", True),
        ("admin-manager", False),
        ("admin-ccs-data-controller", False),
    ])
    def test_framework_action_list_includes_manage_communications(self, role, link_should_be_visible):
        self.user_role = role
        response = self.client.get('/admin')
        assert response.status_code == 200
        document = html.fromstring(response.get_data(as_text=True))
        link_is_visible = bool(document.xpath('.//a[contains(text(),"Manage communications")]'))

        assert link_is_visible is link_should_be_visible, (
            "Role {} {} see the link".format(role, "cannot" if link_should_be_visible else "can")
        )

    @pytest.mark.parametrize("role, link_should_be_visible", [
        ("admin", False),
        ("admin-ccs-category", False),
        ("admin-ccs-sourcing", True),
        ("admin-framework-manager", True),
        ("admin-manager", False),
        ("admin-ccs-data-controller", False),
    ])
    def test_framework_action_list_includes_statistics(self, role, link_should_be_visible):
        self.user_role = role
        response = self.client.get('/admin')
        assert response.status_code == 200
        document = html.fromstring(response.get_data(as_text=True))
        link_is_visible = bool(document.xpath('.//a[contains(text(),"View application statistics")]'))

        assert link_is_visible is link_should_be_visible, (
            "Role {} {} see the link".format(role, "cannot" if link_should_be_visible else "can")
        )

    @pytest.mark.parametrize("role, link_should_be_visible", [
        ("admin", False),
        ("admin-ccs-category", False),
        ("admin-ccs-sourcing", False),
        ("admin-framework-manager", False),
        ("admin-manager", False),
        ("admin-ccs-data-controller", True),
    ])
    @pytest.mark.parametrize('framework_status', ('live', 'standstill', 'pending'))
    def test_data_controller_can_download_supplier_lists_for_certain_framework_statuses_and_dos2(
        self, framework_status, role, link_should_be_visible
    ):
        self.user_role = role
        self.data_api_client.find_frameworks.return_value = {"frameworks": [
            {
                "id": 1,
                "name": "Amazing Digital Framework",
                "slug": "amazing-digital-framework",
                "family": "g-cloud",
                "status": framework_status,
            },
            {
                "id": 2,
                "name": "Digital Outcomes and Specialists 2",
                "slug": "digital-outcomes-and-specialists-2",
                "family": "digital-outcomes-and-specialists",
                "status": 'expired',
            },

        ]}

        response = self.client.get('/admin')
        assert response.status_code == 200
        document = html.fromstring(response.get_data(as_text=True))

        assert bool(document.xpath('.//h2[contains(text(),"Download supplier lists")]')) == link_should_be_visible

        link_is_visible = bool(document.xpath('.//a[contains(text(),"Amazing Digital Framework")]'))
        assert link_is_visible is link_should_be_visible, (
            "Role {} {} see the link".format(role, "cannot" if link_should_be_visible else "can")
        )
        link_is_visible = bool(document.xpath('.//a[contains(text(),"Digital Outcomes and Specialists 2")]'))
        assert link_is_visible is link_should_be_visible, (
            "Role {} {} see the link".format(role, "cannot" if link_should_be_visible else "can")
        )

    @pytest.mark.parametrize("role, link_should_be_visible", [
        ("admin", False),
        ("admin-ccs-category", True),
        ("admin-ccs-sourcing", True),
        ("admin-framework-manager", True),
        ("admin-manager", False),
        ("admin-ccs-data-controller", False),
    ])
    def test_download_g_cloud_outcomes_is_shown_to_users_with_right_roles(self, role, link_should_be_visible):
        self.user_role = role
        response = self.client.get('/admin')
        assert response.status_code == 200
        document = html.fromstring(response.get_data(as_text=True))
        link_is_visible = bool(document.xpath('.//a[@href="/admin/direct-award/outcomes"]'))

        assert link_is_visible is link_should_be_visible, (
            "Role {} {} see the link".format(role, "cannot" if link_should_be_visible else "can")
        )
