import mock
import re
import os

from dmutils.user import User
from flask import json

from app import create_app
from app import login_manager
from unittest import TestCase


class BaseApplicationTest(TestCase):
    def setUp(self):
        self.app = create_app('test')
        self.client = self.app.test_client()

        self._s3_patch = mock.patch('app.main.views.services.S3')
        self.s3 = self._s3_patch.start()

        self._default_suffix_patch = mock.patch(
            'dmutils.documents.default_file_suffix',
            return_value='2015-01-01-1200'
        )
        self._default_suffix_patch.start()

        self._user_callback = login_manager.user_callback

        def user_loader(user_id):
            if user_id:
                return User(
                    user_id, 'test@example.com', None, None, False, True, 'tester', 'admin'
                )

        login_manager.user_loader(user_loader)

    def tearDown(self):
        self._s3_patch.stop()
        self._default_suffix_patch.stop()
        login_manager.user_loader(self._user_callback)

    def load_example_listing(self, name):
        file_path = os.path.join("example_responses", "{}.json".format(name))
        with open(file_path) as f:
            return json.load(f)

    @staticmethod
    def strip_all_whitespace(content):
        pattern = re.compile(r'\s+')
        return re.sub(pattern, '', content)


class Response:
    def __init__(self, status_code=503, message=None):
        self._status_code = status_code
        self._message = message

    @property
    def message(self):
        return self._message

    @property
    def status_code(self):
        return self._status_code


class LoggedInApplicationTest(BaseApplicationTest):
    def setUp(self):
        super(LoggedInApplicationTest, self).setUp()
        patch_config = {
            'authenticate_user.return_value': {
                'users': {
                    'id': 1234,
                    'emailAddress': 'test@example.com',
                    'role': 'admin',
                    'locked': False,
                    'passwordChangedAt': '2015-01-01T00:00:00Z',
                    'active': True,
                    'name': 'tester'
                }
            }
        }
        self._data_api_client = mock.patch(
            'app.main.views.login.data_api_client',
            **patch_config
        )
        self._data_api_client.start()
        res = self.client.post('/admin/login', data={
            'email_address': 'test@example.com',
            'password': '1234567890'
        })

    def tearDown(self):
        self._data_api_client.stop()

    def _replace_whitespace(self, string, replacement_substring=""):
            # Replace all runs of whitespace with replacement_substring
            return re.sub(r"\s+", replacement_substring, string)
