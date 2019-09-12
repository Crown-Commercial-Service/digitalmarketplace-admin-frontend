# coding=utf-8
from io import BytesIO
from urllib.parse import urljoin

import mock
import pytest
from lxml import html

from dmtestutils.api_model_stubs import FrameworkStub
from dmtestutils.comparisons import RestrictedAny
from dmtestutils.fixtures import valid_pdf_bytes

from ...helpers import LoggedInApplicationTest


class _BaseTestCommunicationsView(LoggedInApplicationTest):
    user_role = 'admin-framework-manager'

    def setup_method(self, method):
        super().setup_method(method)
        self.framework_slug = "g-things-23"
        self.framework_stub = FrameworkStub(slug=self.framework_slug)
        self.data_api_client_patch = mock.patch('app.main.views.communications.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()

        # note how this evaluates .single_result_response() at call-time, allowing self.framework_stub to be
        # overridden by test methods
        self.data_api_client.get_framework.side_effect = lambda framework_slug: {
            self.framework_slug: self.framework_stub.single_result_response()
        }[framework_slug]

        self.app.config["DM_COMMUNICATIONS_BUCKET"] = "flop-slop-slap"
        self.app.config["DM_ASSETS_URL"] = "https://basket.market.net/"

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)


class TestManageCommunicationsView(_BaseTestCommunicationsView):
    @pytest.mark.parametrize("role,expected_code", [
        ("admin", 403),
        ("admin-ccs-category", 403),
        ("admin-ccs-sourcing", 403),
        ("admin-framework-manager", 200),
        ("admin-manager", 403),
    ])
    def test_get_page_should_only_be_accessible_to_specific_user_roles(self, role, expected_code):
        self.user_role = role
        response = self.client.get("/admin/communications/{}".format(self.framework_slug))
        actual_code = response.status_code
        assert actual_code == expected_code, "Unexpected response {} for role {}".format(actual_code, role)

    def test_page_shows_empty_messages_if_no_files_uploaded(self):
        self.s3.return_value.list.side_effect = lambda *args, **kwargs: []  # return a fresh empty list every time
        response = self.client.get("/admin/communications/{}".format(self.framework_slug))
        document = html.fromstring(response.get_data(as_text=True))
        file_upload_messages = document.xpath('//p[@class="summary-item-no-content"]')

        assert len(file_upload_messages) == 2
        assert file_upload_messages[0].text_content().strip() == "No communications files"
        assert file_upload_messages[1].text_content().strip() == "No clarification answers"

        assert self.data_api_client.mock_calls == [
            mock.call.get_framework(self.framework_slug)
        ]
        assert self.s3.mock_calls == [
            mock.call("flop-slop-slap"),
            mock.call().list('g-things-23/communications/updates/communications', load_timestamps=True),
            mock.call().list('g-things-23/communications/updates/clarifications', load_timestamps=True),
        ]

    @pytest.mark.parametrize("framework_status", ("open", "standstill",))
    def test_page_shows_timestamp_from_last_file_in_list_if_some_files_already_uploaded(self, framework_status):
        self.framework_stub = FrameworkStub(slug=self.framework_slug, status=framework_status)
        self.s3.return_value.list.side_effect = lambda prefix, *args, **kwargs: {
            "g-things-23/communications/updates/communications": [
                {
                    "path": "g-things-23/communications/updates/communications/communication-foo.pdf",
                    "last_modified": "2018-01-01T01:01:01.000001Z",
                    "filename": "clarification-foo.pdf",
                },
                {
                    "path": "g-things-23/communications/updates/communications/communication-bar.pdf",
                    "last_modified": "2018-02-02T02:02:02.000002Z",
                    "filename": "clarification-bar.pdf",
                },
                {
                    "path": "g-things-23/communications/updates/communications/communication-baz.pdf",
                    "last_modified": "2018-03-03T03:03:03.000003Z",
                    "filename": "clarification-baz.pdf",
                },
            ],
            "g-things-23/communications/updates/clarifications": [
                {
                    "path": "g-things-23/communications/updates/clarifications/clarification-qux.pdf",
                    "last_modified": "2018-04-04T01:01:01.000001Z",
                    "filename": "clarification-qux.pdf",
                },
                {
                    "path": "g-things-23/communications/updates/clarifications/clarification-dax.pdf",
                    "last_modified": "2018-07-25T02:02:02.000002Z",
                    "filename": "clarification-dax.pdf",
                },
            ],
        }[prefix]
        response = self.client.get("/admin/communications/{}".format(self.framework_slug))
        assert response.status_code == 200
        doc = html.fromstring(response.get_data(as_text=True))

        assert tuple(
            tuple(
                (
                    # date text
                    row.xpath("normalize-space(string(./td[1]))"),
                    # download href
                    row.xpath("./td[2]//a/@href")[0],
                    # download text
                    row.xpath("normalize-space(string(./td[2]//a))"),
                    # delete href
                    row.xpath("./td[3]//a[normalize-space(string())='Delete']/@href")[0],
                ) for row in table.xpath(".//tr[@class='summary-item-row']")
            ) for table in doc.xpath("//table[./caption[normalize-space(text())='Communications present']]")
        ) == (
            (
                (
                    'Monday 1 January 2018',
                    '/admin/communications/g-things-23/files/communication/communication-foo.pdf',
                    'document: clarification-foo.pdf',
                    '/admin/communications/g-things-23/delete/communication/communication-foo.pdf',
                ),
                (
                    'Friday 2 February 2018',
                    '/admin/communications/g-things-23/files/communication/communication-bar.pdf',
                    'document: clarification-bar.pdf',
                    '/admin/communications/g-things-23/delete/communication/communication-bar.pdf',
                ),
                (
                    'Saturday 3 March 2018',
                    '/admin/communications/g-things-23/files/communication/communication-baz.pdf',
                    'document: clarification-baz.pdf',
                    '/admin/communications/g-things-23/delete/communication/communication-baz.pdf',
                ),
            ),
        ) + ((
            (
                (
                    'Wednesday 4 April 2018',
                    '/admin/communications/g-things-23/files/clarification/clarification-qux.pdf',
                    'document: clarification-qux.pdf',
                    '/admin/communications/g-things-23/delete/clarification/clarification-qux.pdf',
                ),
                (
                    'Wednesday 25 July 2018',
                    '/admin/communications/g-things-23/files/clarification/clarification-dax.pdf',
                    'document: clarification-dax.pdf',
                    '/admin/communications/g-things-23/delete/clarification/clarification-dax.pdf',
                ),
            ),
        ) if framework_status == "open" else ())

        # find the form that has our submit button
        form = doc.xpath(
            "//form[@method='post'][@enctype='multipart/form-data'][.//button[contains(text(),'Upload files')]]"
        )[0]
        # should be a self-posting form
        assert urljoin(
            f"http://localhost/admin/communications/{self.framework_slug}",
            form.attrib.get("action", ""),
        ) == f"http://localhost/admin/communications/{self.framework_slug}"

        assert form.xpath(".//input[@name='csrf_token']")
        assert form.xpath(
            ".//input[@name='communication'][@type='file']"
        )
        assert bool(doc.xpath(
            ".//input[@name='clarification'][@type='file']"
        )) == (framework_status == "open")

        assert self.data_api_client.mock_calls == [
            mock.call.get_framework(self.framework_slug)
        ]
        assert self.s3.mock_calls == [
            mock.call("flop-slop-slap"),
            mock.call().list('g-things-23/communications/updates/communications', load_timestamps=True),
            mock.call().list('g-things-23/communications/updates/clarifications', load_timestamps=True),
        ]


class TestUploadCommunicationsView(_BaseTestCommunicationsView):
    def test_post_documents_for_framework(self):
        response = self.client.post(
            f"/admin/communications/{self.framework_slug}",
            data={
                'communication': (BytesIO(valid_pdf_bytes), 'test-comm.pdf'),
                'clarification': (BytesIO(valid_pdf_bytes), 'test-clar.pdf'),
            }
        )

        # check that we did actually mock-send two files
        assert self.s3.mock_calls == [
            mock.call('flop-slop-slap'),
            mock.call().save(
                f'{self.framework_slug}/communications/updates/communications/test-comm.pdf',
                RestrictedAny(lambda other: other.filename == "test-comm.pdf"),
                acl='bucket-owner-full-control',
                download_filename='test-comm.pdf',
            ),
            mock.call().save(
                f'{self.framework_slug}/communications/updates/clarifications/test-clar.pdf',
                RestrictedAny(lambda other: other.filename == "test-clar.pdf"),
                acl='bucket-owner-full-control',
                download_filename='test-clar.pdf',
            ),
        ]
        self.assert_flashes('New communication was uploaded.')
        self.assert_flashes('New clarification was uploaded.')

        assert response.status_code == 302
        # should basically be redirecting back to ourselves
        assert urljoin(
            f"http://localhost/admin/communications/{self.framework_slug}",
            response.location,
        ) == f"http://localhost/admin/communications/{self.framework_slug}"

    @pytest.mark.parametrize("disallowed_role", ["admin", "admin-ccs-category", "admin-ccs-sourcing", "admin-manager"])
    def test_disallowed_roles_can_not_post_documents_for_framework(self, disallowed_role):
        self.user_role = disallowed_role

        response = self.client.post(
            f"/admin/communications/{self.framework_slug}",
            data={
                'communication': (BytesIO(valid_pdf_bytes), 'test-comm.pdf'),
                'clarification': (BytesIO(valid_pdf_bytes), 'test-clar.pdf'),
            }
        )
        assert response.status_code == 403
        # nothing was uploaded
        assert self.s3.mock_calls == []

        self.assert_no_flashes()

    def test_post_bad_documents_for_framework(self):

        response = self.client.post(
            f"/admin/communications/{self.framework_slug}",
            data={
                'communication': (BytesIO(valid_pdf_bytes), 'test-comm.unknown'),
                'clarification': (BytesIO(valid_pdf_bytes), 'test-clar.unknown'),
            }
        )

        self.assert_flashes('Communication file is not an open document format or a CSV.', expected_category='error')
        self.assert_flashes('Clarification file is not a PDF.', expected_category='error')

        assert response.status_code == 302
        # should basically be redirecting back to ourselves
        assert urljoin(
            f"http://localhost/admin/communications/{self.framework_slug}",
            response.location,
        ) == f"http://localhost/admin/communications/{self.framework_slug}"

        # nothing was uploaded
        assert self.s3.mock_calls == [mock.call('flop-slop-slap')]


class TestDownloadCommunicationsView(_BaseTestCommunicationsView):
    @pytest.mark.parametrize("disallowed_role", ["admin", "admin-ccs-category", "admin-ccs-sourcing", "admin-manager"])
    @pytest.mark.parametrize("comm_type", ("communication", "clarification",))
    def test_disallowed_roles(self, comm_type, disallowed_role):
        self.user_role = disallowed_role

        response = self.client.get(
            f"/admin/communications/{self.framework_slug}/files/{comm_type}/floating/foampool.pdf",
        )
        assert response.status_code == 403

        # no signed url was created
        assert self.s3.mock_calls == []

        assert self.data_api_client.mock_calls == []

    @pytest.mark.parametrize("comm_type", ("communication", "clarification",))
    def test_happy_path(self, comm_type):
        self.s3.return_value.get_signed_url.return_value = "https://bounded.in.barrels/green/goldenly/lagoons.pdf"
        response = self.client.get(
            f"/admin/communications/{self.framework_slug}/files/{comm_type}/floating/foampool.pdf",
        )

        assert response.status_code == 302
        assert response.location == "https://basket.market.net/green/goldenly/lagoons.pdf"

        assert self.s3.mock_calls == [
            mock.call('flop-slop-slap'),
            mock.call().get_signed_url(
                f'{self.framework_slug}/communications/updates/{comm_type}s/floating/foampool.pdf'
            ),
        ]
        # should have checked framework exists
        assert self.data_api_client.mock_calls == [
            mock.call.get_framework(self.framework_slug)
        ]

    def test_invalid_comm_type(self):
        response = self.client.get(
            f"/admin/communications/{self.framework_slug}/files/seasnakes/floating/foampool.pdf",
        )

        assert response.status_code == 404

        # no signed url was created
        assert self.s3.mock_calls == []

        assert self.data_api_client.mock_calls == []

    @pytest.mark.parametrize("comm_type", ("communication", "clarification",))
    def test_non_present_file(self, comm_type):
        self.s3.return_value.get_signed_url.return_value = None
        response = self.client.get(
            f"/admin/communications/{self.framework_slug}/files/{comm_type}/floating/foampool.pdf",
        )

        assert response.status_code == 404

        assert self.s3.mock_calls == [
            mock.call('flop-slop-slap'),
            mock.call().get_signed_url(
                f'{self.framework_slug}/communications/updates/{comm_type}s/floating/foampool.pdf'
            ),
        ]
        # should have checked framework exists
        assert self.data_api_client.mock_calls == [
            mock.call.get_framework(self.framework_slug)
        ]

    @pytest.mark.parametrize("comm_type", ("communication", "clarification",))
    def test_spurious_double_dot(self, comm_type):
        self.s3.return_value.get_signed_url.return_value = None
        response = self.client.get(
            f"/admin/communications/{self.framework_slug}/files/{comm_type}/../floating/foampool.pdf",
        )

        assert response.status_code == 404

        assert self.s3.mock_calls == []
        assert self.data_api_client.mock_calls == []


class TestDeleteCommunicationsConfirmationPage(_BaseTestCommunicationsView):
    @pytest.mark.parametrize("disallowed_role", ["admin", "admin-ccs-category", "admin-ccs-sourcing", "admin-manager"])
    @pytest.mark.parametrize("comm_type", ("communication", "clarification",))
    def test_disallowed_roles(self, comm_type, disallowed_role):
        self.user_role = disallowed_role

        response = self.client.get(
            f"/admin/communications/{self.framework_slug}/delete/{comm_type}/floating/foampool.pdf",
        )
        assert response.status_code == 403

        assert self.data_api_client.mock_calls == []
        assert self.s3.mock_calls == []
        self.assert_no_flashes()

    def test_invalid_comm_type(self):
        response = self.client.get(
            f"/admin/communications/{self.framework_slug}/delete/seasnakes/floating/foampool.pdf",
        )

        assert response.status_code == 404
        assert self.data_api_client.mock_calls == []
        assert self.s3.mock_calls == []
        self.assert_no_flashes()

    def test_spurious_double_dot(self):
        response = self.client.get(
            f"/admin/communications/{self.framework_slug}/delete/floating/../../../foampool.pdf",
        )

        assert response.status_code == 404
        assert self.data_api_client.mock_calls == []
        assert self.s3.mock_calls == []
        self.assert_no_flashes()

    @pytest.mark.parametrize("comm_type", ("communication", "clarification",))
    def test_happy_path(self, comm_type):
        response = self.client.get(
            f"/admin/communications/{self.framework_slug}/delete/{comm_type}/floating/foampool.pdf",
        )
        assert response.status_code == 200

        doc = html.fromstring(response.get_data(as_text=True))
        assert doc.xpath(
            "//*[normalize-space(string())=$t]",
            t=(
                f"Are you sure you want to delete the {self.framework_stub.response()['name']} {comm_type} "
                "file ‘floating/foampool.pdf’?"
            ),
        )

        # find the form that has our submit button
        form = doc.xpath(
            "//form[@method='POST'][.//input[@name='csrf_token']]"
            "[.//button[@name='confirm'][contains(text(), 'Delete file')]]"
        )[0]
        # should be a self-posting form
        assert urljoin(
            f"http://localhost/admin/communications/{self.framework_slug}/delete/{comm_type}/floating/foampool.pdf",
            form.attrib.get("action", ""),
        ) == f"http://localhost/admin/communications/{self.framework_slug}/delete/{comm_type}/floating/foampool.pdf"

        # should have checked framework exists
        assert self.data_api_client.mock_calls == [
            mock.call.get_framework(self.framework_slug)
        ]
        # no use of bucket in GET request
        assert self.s3.mock_calls == []
        self.assert_no_flashes()


class TestDeleteCommunicationsPost(_BaseTestCommunicationsView):
    @pytest.mark.parametrize("disallowed_role", ["admin", "admin-ccs-category", "admin-ccs-sourcing", "admin-manager"])
    @pytest.mark.parametrize("comm_type", ("communication", "clarification",))
    def test_disallowed_roles(self, comm_type, disallowed_role):
        self.user_role = disallowed_role

        response = self.client.post(
            f"/admin/communications/{self.framework_slug}/delete/{comm_type}/floating/foampool.pdf",
            data={"confirm": "Delete file"},
        )
        assert response.status_code == 403

        assert self.data_api_client.mock_calls == []
        assert self.s3.mock_calls == []
        self.assert_no_flashes()

    def test_invalid_comm_type(self):
        response = self.client.post(
            f"/admin/communications/{self.framework_slug}/delete/seasnakes/floating/foampool.pdf",
            data={"confirm": "Delete file"},
        )

        assert response.status_code == 404
        assert self.data_api_client.mock_calls == []
        assert self.s3.mock_calls == []
        self.assert_no_flashes()

    def test_spurious_double_dot(self):
        response = self.client.post(
            f"/admin/communications/{self.framework_slug}/delete/floating/../../../foampool.pdf",
            data={"confirm": "Delete file"},
        )

        assert response.status_code == 404
        assert self.data_api_client.mock_calls == []
        assert self.s3.mock_calls == []
        self.assert_no_flashes()

    @pytest.mark.parametrize("comm_type", ("communication", "clarification",))
    @pytest.mark.parametrize("file_path", (
        "floating/foampool.pdf",
        "floatingfoampool",
    ))
    def test_happy_path(self, comm_type, file_path):
        self.s3.return_value.path_exists.return_value = True
        response = self.client.post(
            f"/admin/communications/{self.framework_slug}/delete/{comm_type}/{file_path}",
            data={"confirm": "Delete file"},
        )
        assert response.status_code == 302
        assert urljoin(
            f"http://localhost/admin/communications/{self.framework_slug}/delete/{comm_type}/{file_path}",
            response.location,
        ) == f"http://localhost/admin/communications/{self.framework_slug}"

        # should have checked framework exists
        assert self.data_api_client.mock_calls == [
            mock.call.get_framework(self.framework_slug)
        ]

        assert self.s3.mock_calls == [
            mock.call('flop-slop-slap'),
            mock.call().path_exists(
                f'{self.framework_slug}/communications/updates/{comm_type}s/{file_path}'
            ),
            mock.call().delete_key(f'{self.framework_slug}/communications/updates/{comm_type}s/{file_path}'),
        ]
        self.assert_flashes(
            f"{comm_type.capitalize()} ‘{file_path}’ was "
            f"deleted for {self.framework_stub.response()['name']}."
        )

    @pytest.mark.parametrize("comm_type", ("communication", "clarification",))
    def test_file_not_present(self, comm_type):
        self.s3.return_value.path_exists.return_value = False
        response = self.client.post(
            f"/admin/communications/{self.framework_slug}/delete/{comm_type}/floating/foampool.pdf",
            data={"confirm": "Delete file"},
        )
        assert response.status_code == 404

        # should have checked framework exists
        assert self.data_api_client.mock_calls == [
            mock.call.get_framework(self.framework_slug)
        ]

        assert self.s3.mock_calls == [
            mock.call('flop-slop-slap'),
            mock.call().path_exists(f'{self.framework_slug}/communications/updates/{comm_type}s/floating/foampool.pdf'),
            # no deletion call
        ]
        self.assert_no_flashes()

    @pytest.mark.parametrize("comm_type", ("communication", "clarification",))
    def test_not_confirmed(self, comm_type):
        self.s3.return_value.path_exists.return_value = True
        response = self.client.post(
            f"/admin/communications/{self.framework_slug}/delete/{comm_type}/floating/foampool.pdf",
            data={"maybe": "perhaps"},
        )
        assert response.status_code == 400

        # should have checked framework exists
        assert self.data_api_client.mock_calls == [
            mock.call.get_framework(self.framework_slug)
        ]

        # no bucket actions took place
        assert self.s3.mock_calls == []
        self.assert_no_flashes()
