import csv

import mock
import pytest

from dmtestutils.api_model_stubs import FrameworkStub

from ...helpers import LoggedInApplicationTest


class TestDirectAwardView(LoggedInApplicationTest):
    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.outcomes.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    @pytest.mark.parametrize("role,expected_code", [
        ("admin", 403),
        ("admin-manager", 403),
        ("admin-ccs-category", 200),
        ("admin-ccs-sourcing", 200),
        ("admin-framework-manager", 200),
    ])
    def test_outcomes_csv_download_permissions(self, role, expected_code):
        self.user_role = role
        response = self.client.get('/admin/direct-award/outcomes')
        actual_code = response.status_code
        assert actual_code == expected_code, "Unexpected response {} for role {}".format(actual_code, role)

    def test_outcomes_csv_download_content(self):
        self.user_role = 'admin-ccs-sourcing'
        find_direct_award_projects_result = {
            "links": {
                "self": "http://localhost:5000/direct-award/projects?latest-first=1&user-id=19175"
            },
            "meta": {
                "total": 20
            },
            "projects": [
                {
                    "active": True,
                    "createdAt": "2018-06-22T10:41:31.281853Z",
                    "downloadedAt": None,
                    "id": 731851428862851,
                    "lockedAt": None,
                    "name": "gfgffd",
                    "outcome": {
                        "result": "cancelled"
                    },
                    "users": [
                        {
                            "active": True,
                            "emailAddress": "buyer@example.com",
                            "id": 123,
                            "name": "A Buyer",
                            "role": "buyer"
                        }
                    ]
                },
                {
                    "active": True,
                    "createdAt": "2018-06-19T13:36:37.557144Z",
                    "downloadedAt": "2018-06-19T13:37:30.849304Z",
                    "id": 272774709812396,
                    "lockedAt": "2018-06-19T13:37:03.176398Z",
                    "name": "22",
                    "outcome": {
                        "award": {
                            "awardValue": "1234.00",
                            "awardingOrganisationName": "123321",
                            "endDate": "2020-12-12",
                            "startDate": "2002-12-12"
                        },
                        "completed": True,
                        "completedAt": "2018-06-19T13:37:59.713497Z",
                        "id": 680306864633356,
                        "result": "awarded",
                        "resultOfDirectAward": {
                            "archivedService": {
                                "id": 266018,
                                "service": {
                                    "id": "316684326093280"
                                }
                            },
                            "project": {
                                "id": 272774709812396
                            },
                            "search": {
                                "id": 3706
                            }
                        }
                    },
                    "users": [
                        {
                            "active": True,
                            "emailAddress": "buyer@example.com",
                            "id": 123,
                            "name": "A Buyer",
                            "role": "buyer"
                        }
                    ]
                }
            ]
        }

        get_archived_service_result = {
            'services': {
                'supplierId': 266018,
                'supplierName': 'Somerford Associates Limited',
                'serviceName': 'testServiceName'
            }
        }

        self.data_api_client.get_archived_service.return_value = get_archived_service_result
        self.data_api_client.find_direct_award_projects.return_value = find_direct_award_projects_result

        response = self.client.get('/admin/direct-award/outcomes')
        assert response.status_code == 200
        assert response.content_type == 'text/csv; charset=utf-8'
        response_data = str(response.data, 'utf-8').splitlines()  # convert byte-string to string
        data = csv.reader(response_data)
        assert data  # checks if CSV is valid

        rows = []
        for row in data:
            rows.append(row)

        # checks that only awarded outcomes are shown
        assert len(rows) == 2

        # checks headers
        assert rows[0] == [
            'ID', 'Name', 'Submitted at', 'Result',
            'Award service ID', 'Award service name',
            'Award supplier id', 'Award supplier name',
            'Award value', 'Awarding organisation name',
            'Award start date', 'Award end date',
            'User id', 'User name', 'User email'
        ]

        # checks results
        assert rows[1] == [
            '272774709812396', '22', '2018-06-19T13:37:59.713497Z', 'awarded',
            '316684326093280', 'testServiceName', '266018', 'Somerford Associates Limited',
            '1234.00', '123321', '2002-12-12', '2020-12-12',
            '123', 'A Buyer', 'buyer@example.com'
        ]


class TestDOSView(LoggedInApplicationTest):

    url = "/admin/digital-outcomes-and-specialists/outcomes"

    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.outcomes.data_api_client', autospec=True)
        self.data_api_client = self.data_api_client_patch.start()

        self.data_api_client.find_frameworks.return_value = {"frameworks": [
            FrameworkStub(
                slug="digital-outcomes-and-specialists-4", status="live"
            ).response()
        ]}

    def teardown_method(self, method):
        self.data_api_client_patch.stop()
        super().teardown_method(method)

    @pytest.fixture(autouse=True)
    def s3(self):
        with mock.patch("app.main.views.outcomes.s3") as s3:
            bucket = s3.S3()
            bucket.get_signed_url.side_effect = \
                lambda path: f"https://s3.example.com/{path}?signature=deadbeef"
            yield s3

    @pytest.mark.parametrize("role,expected_code", [
        ("admin", 403),
        ("admin-manager", 403),
        ("admin-ccs-category", 302),
        ("admin-ccs-sourcing", 302),
        ("admin-framework-manager", 302),
    ])
    def test_download_permissions(self, role, expected_code):
        self.user_role = role
        response = self.client.get(self.url)
        actual_code = response.status_code
        assert actual_code == expected_code, "Unexpected response {} for role {}".format(actual_code, role)

    def test_redirects_to_assets_domain(self):
        self.user_role = "admin-ccs-category"

        response = self.client.get(self.url)
        assert response.status_code == 302
        assert response.location \
            == "https://assets.test.digitalmarketplace.service.gov.uk" \
            "/digital-outcomes-and-specialists-4/reports/opportunity-data.csv" \
            "?signature=deadbeef"

    @pytest.mark.parametrize("latest_dos_framework", (
        "digital-outcomes-and-specialists-4",
        "digital-outcomes-and-specialists-5",
    ))
    def test_csv_is_for_latest_live_dos_framework(self, latest_dos_framework, s3):
        self.user_role = "admin-ccs-category"

        self.data_api_client.find_frameworks.return_value = {"frameworks": [
            FrameworkStub(
                framework_live_at="2016-03-03 12:00:00",
                slug="digital-outcomes-and-specialists",
                status="expired"
            ).response(),
            FrameworkStub(
                framework_live_at="2018-10-01 10:58:09.43134",
                slug="digital-outcomes-and-specialists-3",
                status="live"
            ).response(),
            FrameworkStub(
                framework_live_at="2019-12-18 15:13:24.53636",
                slug=latest_dos_framework,
                status="live"
            ).response(),
            FrameworkStub(
                framework_live_at="2020-12-18 15:13:24.53636",
                slug="g-cloud-12",
                status="live"
            ).response(),
        ]}

        response = self.client.get(self.url)

        assert s3.S3().get_signed_url.call_args == mock.call(
            f"{latest_dos_framework}/reports/opportunity-data.csv"
        )
        assert latest_dos_framework in response.location
