# coding=utf-8
from io import BytesIO

import mock
import pytest
from lxml import html

from ...helpers import LoggedInApplicationTest


@mock.patch('app.main.views.communications.data_api_client.get_framework', return_value={"frameworks": []})
class TestCommunicationsView(LoggedInApplicationTest):
    user_role = 'admin-framework-manager'

    def setup_method(self, method, *args, **kwargs):
        super(TestCommunicationsView, self).setup_method(method, *args, **kwargs)
        self.dummy_file = BytesIO(u'Lorem ipsum dolor sit amet'.encode('utf8'))
        self.framework_slug = self.load_example_listing('framework_response')['frameworks']['slug']

    @pytest.mark.parametrize("role,expected_code", [
        ("admin", 403),
        ("admin-ccs-category", 403),
        ("admin-ccs-sourcing", 403),
        ("admin-framework-manager", 200),
        ("admin-manager", 403),
    ])
    def test_get_page_should_only_be_accessible_to_specific_user_roles(self, get_framework_mock, role, expected_code):
        self.user_role = role
        response = self.client.get("/admin/communications/{}".format(self.framework_slug))
        actual_code = response.status_code
        assert actual_code == expected_code, "Unexpected response {} for role {}".format(actual_code, role)

    def test_page_shows_empty_messages_if_no_files_uploaded(self, get_framework_mock):
        self.s3.return_value.list.side_effect = ([], [])  # Empty lists for both communication and clarification files
        get_framework_mock.return_value = {"frameworks": {"status": "open"}}
        response = self.client.get("/admin/communications/{}".format(self.framework_slug))
        document = html.fromstring(response.get_data(as_text=True))
        file_upload_messages = document.xpath('//p[@class="file-upload-existing-value"]')

        assert len(file_upload_messages) == 2
        assert file_upload_messages[0].text_content().strip() == "No communications have been uploaded yet"
        assert file_upload_messages[1].text_content().strip() == "No clarification answers have been uploaded yet"

    def test_page_shows_timestamp_from_last_file_in_list_if_some_files_already_uploaded(self, get_framework_mock):
        # The first list is for communication files, the second for clarifications
        self.s3.return_value.list.side_effect = (
            [
                {
                    "path": "g-things-23/communications/updates/communications/communication-1.pdf",
                    "last_modified": "2018-01-01T01:01:01.000001Z"
                },
                {
                    "path": "g-things-23/communications/updates/communications/communication-2.pdf",
                    "last_modified": "2018-02-02T02:02:02.000002Z"
                },
                {
                    "path": "g-things-23/communications/updates/communications/communication-3.pdf",
                    "last_modified": "2018-03-03T03:03:03.000003Z"
                },
            ],
            [
                {
                    "path": "g-things-23/communications/updates/clarifiactions/clarification-1.pdf",
                    "last_modified": "2018-04-04T01:01:01.000001Z"
                },
                {
                    "path": "g-things-23/communications/updates/clarifiactions/clarification-2.pdf",
                    "last_modified": "2018-07-25T02:02:02.000002Z"  # Test GMT/BST pretty formatting while we're here
                },
            ],
        )
        get_framework_mock.return_value = {"frameworks": {"status": "open"}}
        response = self.client.get("/admin/communications/{}".format(self.framework_slug))
        document = html.fromstring(response.get_data(as_text=True))
        file_upload_messages = document.xpath('//p[@class="file-upload-existing-value"]')

        assert len(file_upload_messages) == 2
        assert file_upload_messages[0].text_content().strip() == "Last modified Saturday 3 March 2018 at 3:03am GMT"
        assert file_upload_messages[1].text_content().strip() == "Last modified Wednesday 25 July 2018 at 3:02am BST"

    def test_post_documents_for_framework(self, get_framework_mock):

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

    @pytest.mark.parametrize("disallowed_role", ["admin", "admin-ccs-category", "admin-ccs-sourcing", "admin-manager"])
    def test_disallowed_roles_can_not_post_documents_for_framework(self, get_framework_mock, disallowed_role):

        self.user_role = disallowed_role

        response = self.client.post(
            "/admin/communications/{}".format(self.framework_slug),
            data={
                'communication': (self.dummy_file, 'test-comm.pdf'),
                'clarification': (self.dummy_file, 'test-clar.pdf'),
            }
        )
        assert response.status_code == 403

    def test_post_bad_documents_for_framework(self, get_framework_mock):

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

    def test_communications_file_saves_with_correct_path(self, get_framework_mock):

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
            acl='bucket-owner-full-control',
            download_filename='test-comm.pdf'
        )

    def test_clarification_file_saves_with_correct_path(self, get_framework_mock):

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
            acl='bucket-owner-full-control',
            download_filename='test-comm.pdf'
        )
