import unittest
import datetime

import mock
from app.main.helpers.s3 import S3


class TestS3Uploader(unittest.TestCase):
    def setUp(self):
        self.s3_mock = mock.Mock()
        self._boto_patch = mock.patch(
            'app.main.helpers.s3.boto.connect_s3',
            return_value=self.s3_mock
        )
        self._boto_patch.start()

    def tearDown(self):
        self._boto_patch.stop()

    def test_get_bucket(self):
        S3('test-bucket')
        self.s3_mock.get_bucket.assert_called_with('test-bucket')

    def test_save_file(self):
        mock_bucket = FakeBucket()
        self.s3_mock.get_bucket.return_value = mock_bucket

        S3('test-bucket').save('/folder', 'test-file.pdf', mock.Mock())
        self.assertEqual(mock_bucket.keys, set(['/folder/test-file.pdf']))

    def test_save_existing_file(self):
        mock_bucket = FakeBucket(['/folder/test-file.pdf'])
        self.s3_mock.get_bucket.return_value = mock_bucket
        now = datetime.datetime(2015, 1, 1, 1, 2, 3, 4)

        with mock.patch.object(datetime, 'datetime',
                               mock.Mock(wraps=datetime.datetime)) as patched:
            patched.utcnow.return_value = now
            S3('test-bucket').save('/folder', 'test-file.pdf', mock.Mock())
            self.assertEqual(mock_bucket.keys, set([
                '/folder/test-file.pdf',
                '/folder/2015-01-01T01:02:03.000004-test-file.pdf'
            ]))


class FakeBucket(object):
    def __init__(self, keys=None):
        self.keys = set(keys or [])

    def get_key(self, key):
        if key in self.keys:
            return FakeKey(key)

    def new_key(self, key):
        self.keys.add(key)
        return FakeKey(key)

    def copy_key(self, new_key, *args, **kwargs):
        self.keys.add(new_key)


class FakeKey(object):
    def __init__(self, key):
        self.name = key.split('/')[-1]

    def set_contents_from_file(self, file, headers):
        return mock.Mock()

    def set_acl(self, acl):
        return mock.Mock()
