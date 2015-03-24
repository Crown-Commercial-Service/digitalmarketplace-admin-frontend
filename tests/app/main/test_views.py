try:
    from urlparse import urlsplit
except ImportError:
    from urllib.parse import urlsplit
from ..helpers import BaseApplicationTest
from ..helpers import LoggedInApplicationTest


class TestSession(BaseApplicationTest):
    def test_index(self):
        response = self.client.get('/')
        self.assertEquals(302, response.status_code)

    def test_login(self):
        response = self.client.post('/login', data=dict(
            username="admin",
            password="admin"
        ))
        self.assertEquals(302, response.status_code)
        self.assertEquals("/", urlsplit(response.location).path)

        response = self.client.get('/')
        self.assertEquals(200, response.status_code)

    def test_invalid_login(self):
        response = self.client.post('/login', data=dict(
            username="admin",
            password="wrong"
        ))
        self.assertEquals(200, response.status_code)

        response = self.client.get('/')
        self.assertEquals(302, response.status_code)
        self.assertEquals("/login", urlsplit(response.location).path)


class TestApplication(LoggedInApplicationTest):
    def test_index(self):
        response = self.client.get('/')
        self.assertEquals(200, response.status_code)

    def test_404(self):
        response = self.client.get('/not-found')
        self.assertEquals(404, response.status_code)
