import mock
import pytest

from dmapiclient import HTTPError
from lxml import html

from ...helpers import LoggedInApplicationTest, Response


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
