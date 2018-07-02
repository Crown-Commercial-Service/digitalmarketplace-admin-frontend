from ...helpers import LoggedInApplicationTest
import pytest
import mock
import csv


class TestDirectAwardView(LoggedInApplicationTest):
    def setup_method(self, method):
        super().setup_method(method)
        self.data_api_client_patch = mock.patch('app.main.views.direct_award.data_api_client', autospec=True)
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
