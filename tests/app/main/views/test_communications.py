# coding=utf-8
from __future__ import unicode_literals

import mock
import pytest

from ...helpers import LoggedInApplicationTest
from io import BytesIO
from dmutils import s3


@mock.patch('app.main.views.communications.data_api_client')
class TestCommunicationsView(LoggedInApplicationTest):

    @pytest.mark.parametrize("allowed_role", ["admin", "admin-ccs-category"])
    def test_get_document_upload_page_for_framework(self, data_api_client, allowed_role):
        data_api_client.get_frameworks.return_value = {"frameworks": []}
        self.user_role = allowed_role
        framework_slug = self.load_example_listing('framework_response')['frameworks']['slug']

        response = self.client.get("/admin/communications/{}".format(framework_slug))
        assert response.status_code == 200

    def test_get_document_upload_page_not_allowed_for_ccs_sourcing(self, data_api_client):
        data_api_client.get_frameworks.return_value = {"frameworks": []}
        self.user_role = "admin-ccs-sourcing"
        framework_slug = self.load_example_listing('framework_response')['frameworks']['slug']

        response = self.client.get("/admin/communications/{}".format(framework_slug))
        assert response.status_code == 403

    @pytest.mark.parametrize("allowed_role", ["admin", "admin-ccs-category"])
    def test_post_documents_for_framework(self, data_api_client, allowed_role):
        # check we are mocking s3 as we must not actually post there!
        assert isinstance(s3.S3, mock.Mock)

        data_api_client.get_frameworks.return_value = {"frameworks": []}
        self.user_role = allowed_role
        framework_slug = self.load_example_listing('framework_response')['frameworks']['slug']
        dummy_file = BytesIO(u'Lorem ipsum dolor sit amet'.encode('utf8'))

        response = self.client.post(
            "/admin/communications/{}".format(framework_slug),
            data={
                'communication': (dummy_file, 'test-comm.pdf'),
                'clarification': (dummy_file, 'test-clar.pdf'),
            }
        )

        # check that we did actually mock-send two files
        self.s3.return_value.save.call_count == 2
        flash_messages = self._get_flash_messages()
        # arguably a misunderstanding here about what an appropriate 'message category' looks like
        assert set(flash_messages.getlist('upload_communication')) == set(('clarification', 'communication',))

        assert response.status_code == 302

    def test_ccs_sourcing_can_not_post_documents_for_framework(self, data_api_client):
        # check we are mocking s3 as we must not actually post there!
        assert isinstance(s3.S3, mock.Mock)

        data_api_client.get_frameworks.return_value = {"frameworks": []}
        self.user_role = "admin-ccs-sourcing"
        framework_slug = self.load_example_listing('framework_response')['frameworks']['slug']
        dummy_file = BytesIO(u'Lorem ipsum dolor sit amet'.encode('utf8'))

        response = self.client.post(
            "/admin/communications/{}".format(framework_slug),
            data={
                'communication': (dummy_file, 'test-comm.pdf'),
                'clarification': (dummy_file, 'test-clar.pdf'),
            }
        )
        assert response.status_code == 403

    def test_post_bad_documents_for_framework(self, data_api_client):
        data_api_client.get_frameworks.return_value = {"frameworks": []}

        framework_slug = self.load_example_listing('framework_response')['frameworks']['slug']
        dummy_file = BytesIO(u'Lorem ipsum dolor sit amet'.encode('utf8'))

        self.client.post(
            "/admin/communications/{}".format(framework_slug),
            data={
                'communication': (dummy_file, 'test-comm.unknown'),
                'clarification': (dummy_file, 'test-clar.unknown'),
            }
        )

        flash_messages = self._get_flash_messages()
        # definitely a misunderstanding here about what an appropriate 'message category' looks like
        assert flash_messages.get('not_open_document_format_or_csv') == 'communication'
        assert flash_messages.get('not_pdf') == 'clarification'
