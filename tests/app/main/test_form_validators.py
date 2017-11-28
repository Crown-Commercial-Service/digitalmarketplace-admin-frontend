import mock
import pytest

from flask.ext.wtf import Form
from wtforms.fields.core import Field
from wtforms.validators import StopValidation

from app.main.forms import AdminEmailAddressValidator


@mock.patch('app.main.forms.data_api_client')
class TestAdminEmailAddressValidator(object):

    def setup_method(self):
        self.form_mock = mock.MagicMock(Form)
        self.field_mock = mock.MagicMock(Field, data='the_email_address')

        self.validator = AdminEmailAddressValidator(message='The message passed to validator')

    def test_admin_email_address_validator_calls_api(self, data_api_client):
        self.validator(self.form_mock, self.field_mock)
        data_api_client.email_is_valid_for_admin_user.assert_called_once_with('the_email_address')

    def test_admin_email_address_validator_raises_with_invalid_response(self, data_api_client):

        data_api_client.email_is_valid_for_admin_user.return_value = False

        with pytest.raises(StopValidation, match='The message passed to validator'):
            self.validator(self.form_mock, self.field_mock)

    def test_admin_email_address_validator_passes_with_valid_response(self, data_api_client):
        data_api_client.email_is_valid_for_admin_user.return_value = True

        assert self.validator(self.form_mock, self.field_mock) is None
