# coding=utf-8

from .helpers import BaseApplicationTest


class TestApplication(BaseApplicationTest):
    def setup(self):
        super(TestApplication, self).setup()

    def test_response_headers(self):
        response = self.client.get('/admin')

        assert (
            response.headers['cache-control'] ==
            "no-cache"
        )
