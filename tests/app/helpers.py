import mock
from app import create_app
from unittest import TestCase


class BaseApplicationTest(TestCase):
    def setUp(self):
        self.app = create_app('test')
        self.client = self.app.test_client()
        self.s3 = mock.patch('app.main.views.S3').start()
        self.service_loader = mock.Mock()
        self._service_loader_patch = mock.patch(
            'app.main.views.ServiceLoader',
            return_value=self.service_loader
        ).start()

    def tearDown(self):
        self.s3.stop()
        self._service_loader_patch.stop()


class LoggedInApplicationTest(BaseApplicationTest):
    def setUp(self):
        super(LoggedInApplicationTest, self).setUp()
        with self.client.session_transaction() as session:
            session['username'] = 'admin'
