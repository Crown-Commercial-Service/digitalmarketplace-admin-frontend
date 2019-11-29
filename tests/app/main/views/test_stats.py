import mock

from ...helpers import BaseApplicationTest


class TestStats(BaseApplicationTest):

    def setup_method(self, method):
        super().setup_method(method)
        self.pp_id_mapping_patch = mock.patch.dict(
            self.app.config["PERFORMANCE_PLATFORM_ID_MAPPING"],
            {"digital-scaffolding": "beaver-street"},
        )
        self.pp_id_mapping_patch.start()

    def teardown_method(self, method):
        self.pp_id_mapping_patch.stop()
        super().teardown_method(method)

    def test_known_pp_id(self):
        response = self.client.get('/admin/statistics/digital-scaffolding')
        assert response.status_code == 301
        assert response.location == "https://www.gov.uk/performance/beaver-street"

    def test_unknown_pp_id(self):
        response = self.client.get('/admin/statistics/broad-daylight')
        assert response.status_code == 410
