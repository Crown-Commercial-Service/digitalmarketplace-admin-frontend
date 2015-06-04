import mock
from app import create_app
from unittest import TestCase


class BaseApplicationTest(TestCase):
    def setUp(self):
        self.app = create_app('test')
        self.client = self.app.test_client()

        self._s3_patch = mock.patch('app.main.views.S3')
        self.s3 = self._s3_patch.start()

        self._default_suffix_patch = mock.patch(
            'dmutils.validation.default_file_suffix',
            return_value='2015-01-01-1200'
        )
        self._default_suffix_patch.start()

    def tearDown(self):
        self._s3_patch.stop()
        self._default_suffix_patch.stop()


class LoggedInApplicationTest(BaseApplicationTest):
    def setUp(self):
        super(LoggedInApplicationTest, self).setUp()
        with self.client.session_transaction() as session:
            session['username'] = 'admin'
