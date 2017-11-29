# coding=utf-8
from __future__ import unicode_literals

import mock
import pytest

from ...helpers import LoggedInApplicationTest
from io import BytesIO


@mock.patch('app.main.views.communications.data_api_client.get_framework', return_value={"frameworks": []})
class TestCommunicationsView(LoggedInApplicationTest):

    def setup_method(self, method, *args, **kwargs):
        super(TestCommunicationsView, self).setup_method(method, *args, **kwargs)
        self.dummy_file = BytesIO(u'Lorem ipsum dolor sit amet'.encode('utf8'))
        self.framework_slug = self.load_example_listing('framework_response')['frameworks']['slug']

    @pytest.mark.parametrize("role,expected_code", [
        ("admin", 403),
        ("admin-ccs-category", 200),
        ("admin-ccs-sourcing", 403),
        ("admin-manager", 403),
    ])
    def test_get_page_should_only_be_accessible_to_specific_user_roles(self, data_api_client, role, expected_code):
        self.user_role = role
        response = self.client.get("/admin/communications/{}".format(self.framework_slug))
        actual_code = response.status_code
        assert actual_code == expected_code, "Unexpected response {} for role {}".format(actual_code, role)

    @pytest.mark.parametrize("allowed_role", ["admin", "admin-ccs-category"])
    def test_post_documents_for_framework(self, data_api_client, allowed_role):

        self.user_role = allowed_role

        response = self.client.post(
            "/admin/communications/{}".format(self.framework_slug),
            data={
                'communication': (self.dummy_file, 'test-comm.pdf'),
                'clarification': (self.dummy_file, 'test-clar.pdf'),
            }
        )

        # check that we did actually mock-send two files
        self.s3.return_value.save.call_count == 2
        flash_messages = self._get_flash_messages()
        # arguably a misunderstanding here about what an appropriate 'message category' looks like
        assert set(flash_messages.getlist('upload_communication')) == set(('clarification', 'communication',))

        assert response.status_code == 302

    def test_ccs_sourcing_can_not_post_documents_for_framework(self, data_api_client):

        self.user_role = "admin-ccs-sourcing"

        response = self.client.post(
            "/admin/communications/{}".format(self.framework_slug),
            data={
                'communication': (self.dummy_file, 'test-comm.pdf'),
                'clarification': (self.dummy_file, 'test-clar.pdf'),
            }
        )
        assert response.status_code == 403

    def test_post_bad_documents_for_framework(self, data_api_client):

        self.client.post(
            "/admin/communications/{}".format(self.framework_slug),
            data={
                'communication': (self.dummy_file, 'test-comm.unknown'),
                'clarification': (self.dummy_file, 'test-clar.unknown'),
            }
        )

        flash_messages = self._get_flash_messages()
        # definitely a misunderstanding here about what an appropriate 'message category' looks like
        assert flash_messages.get('not_open_document_format_or_csv') == 'communication'
        assert flash_messages.get('not_pdf') == 'clarification'

    def test_communications_file_saves_with_correct_path(self, data_api_client):

        response = self.client.post(
            "/admin/communications/{}".format(self.framework_slug),
            data={
                'communication': (self.dummy_file, 'test-comm.pdf'),
            }
        )

        assert response.status_code == 302
        self.s3.return_value.save.assert_called_once_with(
            '{}/communications/updates/communications/test-comm.pdf'.format(self.framework_slug),
            mock.ANY,  # werkzeug.datastructures.FileStorage object we are saving to s3
            acl='private',
            download_filename='test-comm.pdf'
        )

    def test_clarification_file_saves_with_correct_path(self, data_api_client):

        response = self.client.post(
            "/admin/communications/{}".format(self.framework_slug),
            data={
                'clarification': (self.dummy_file, 'test-comm.pdf'),
            }
        )

        assert response.status_code == 302
        self.s3.return_value.save.assert_called_once_with(
            '{}/communications/updates/clarifications/test-comm.pdf'.format(self.framework_slug),
            mock.ANY,  # werkzeug.datastructures.FileStorage object we are saving to s3
            acl='private',
            download_filename='test-comm.pdf'
        )
