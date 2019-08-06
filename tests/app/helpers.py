from functools import partial
import mock
import re
import os

from dmcontent import ContentLoader
from dmutils.user import User
from flask import json, Blueprint
from werkzeug.datastructures import MultiDict
from flask_login import login_user

from app import create_app, data_api_client, _make_content_loader_factory
from app import login_manager


login_for_tests = Blueprint('login_for_tests', __name__)


@login_for_tests.route('/auto-login')
def auto_login():
    user_json = {"users": {
        'id': 1234,
        'emailAddress': 'test@example.com',
        'role': 'admin',
        'locked': False,
        'passwordChangedAt': '2015-01-01T00:00:00Z',
        'active': True,
        'name': 'tester'
    }}
    user = User.from_json(user_json)
    login_user(user)
    return "OK"


class BaseApplicationTest(object):
    injected_content_loader = ContentLoader('app/content')

    def setup_method(self, method):

        # We need to mock the API client in create_app, however we can't use patch the constructor,
        # as the DataAPIClient instance has already been created; nor can we temporarily replace app.data_api_client
        # with a mock, because then the shared instance won't have been configured (done in create_app). Instead,
        # just mock the one function that would make an API call in this case.
        data_api_client.find_frameworks = mock.Mock()
        data_api_client.find_frameworks.return_value = self._get_frameworks_list_fixture_data()

        # if we don't make this tweak, the content loader will get re-built for every test, which is incredibly slow.
        # instead we replace the `_make_content_loader_factory` with a variant which injects `injected_content_loader`
        # as the `initial_instance` argument, which we keep as a class attribute. `_make_content_loader_factory` still
        # executes inside `create_app`, but all the content it asks to be loaded should already be present in the
        # content_loader it is operating on, so it effectively does nothing.
        # a test that needed a "clean" content loader for some reason would be able to override a test instance's
        # injected_content_loader early in the setup_method process (e.g. with None)
        self.make_content_loader_factory_mock = mock.patch("app._make_content_loader_factory")
        self.make_content_loader_factory_mock.start().side_effect = partial(
            _make_content_loader_factory,
            initial_instance=self.injected_content_loader,
        )

        self.app_env_var_mock = mock.patch.dict('gds_metrics.os.environ', {'PROMETHEUS_METRICS_PATH': '/_metrics'})
        self.app_env_var_mock.start()

        self.app = create_app('test')
        self.client = self.app.test_client()

        self._s3_patch = mock.patch('dmutils.s3.S3')
        self.s3 = self._s3_patch.start()
        self.s3.return_value = mock.Mock()
        self.s3.return_value.list.return_value = []

        self._default_suffix_patch = mock.patch(
            'dmutils.documents.default_file_suffix',
            return_value='2015-01-01-1200'
        )
        self._default_suffix_patch.start()

    def teardown_method(self, method):
        self._s3_patch.stop()
        self._default_suffix_patch.stop()
        self.app_env_var_mock.stop()
        self.make_content_loader_factory_mock.stop()

    def load_example_listing(self, name):
        file_path = os.path.join("example_responses", "{}.json".format(name))
        with open(file_path) as f:
            return json.load(f)

    @staticmethod
    def strip_all_whitespace(content):
        pattern = re.compile(r'\s+')
        return re.sub(pattern, '', content)

    def assert_flashes(self, expected_message, expected_category='message'):
        with self.client.session_transaction() as session:
            if '_flashes' not in session:
                raise AssertionError('nothing flashed')
            messages = MultiDict(session['_flashes'])
            assert expected_message in messages.getlist(expected_category), \
                "Didn't find '{}' in '{}'".format(expected_message, messages.getlist(expected_category))

    def assert_no_flashes(self):
        with self.client.session_transaction() as session:
            assert '_flashes' not in session

    @staticmethod
    def _get_fixture_data(fixture_filename):
        test_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), ".")
        )
        fixture_path = os.path.join(
            test_root, 'fixtures', fixture_filename
        )
        with open(fixture_path) as fixture_file:
            return json.load(fixture_file)

    @staticmethod
    def _get_frameworks_list_fixture_data():
        return BaseApplicationTest._get_fixture_data('frameworks.json')


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
    user_role = 'admin'

    def setup_method(self, method):
        super().setup_method(method)

        self.app.register_blueprint(login_for_tests)

        with mock.patch('app.data_api_client') as login_api_client:
            login_api_client.authenticate_user.return_value = {
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

            res = self.client.get('/auto-login')
            assert res.status_code == 200

        self._user_callback = login_manager.user_callback
        login_manager.user_loader(self.user_loader)

    def user_loader(self, user_id):
        if user_id:
            return User(
                user_id=user_id,
                email_address='test@example.com',
                supplier_id=None,
                supplier_name=None,
                supplier_organisation_size='micro',
                locked=False,
                active=True,
                name='tester',
                role=self.user_role,
                user_research_opted_in=True,
            )

    def teardown_method(self, method):
        login_manager.user_loader(self._user_callback)
        super().teardown_method(method)

    def _replace_whitespace(self, string, replacement_substring=""):
        # Replace all runs of whitespace with replacement_substring
        return re.sub(r"\s+", replacement_substring, string)
