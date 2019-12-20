import mock
import pytest
from flask_wtf import Form
from wtforms.fields.core import Field
from wtforms.validators import StopValidation, ValidationError

from app.main.forms import AdminEmailAddressValidator, NotInDomainSuffixBlacklistValidator

from ..helpers import BaseApplicationTest


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


class TestNotInDomainSuffixBlacklistValidator(BaseApplicationTest):
    def setup_method(self, method):
        super().setup_method(method)
        self.app_context = self.app.app_context()
        self.app_context.push()

        self.form_mock = mock.MagicMock(Form)
        self.field_mock = mock.MagicMock(Field)

        self.validator = NotInDomainSuffixBlacklistValidator("Foo %(matched_suffix)s bar")

    def teardown_method(self, method):
        super().teardown_method(method)
        self.app_context.pop()

    @pytest.mark.parametrize("new_buyer_domain", (
        "kev.uk",
        "zz",
        "keyes.ORG.uk",
        ".GOV",
        "om",  # a suffix of "com", but not if the validator's assuming an implicit preceding separator, which it should
    ))
    def test_success(self, new_buyer_domain):
        self.field_mock.data = new_buyer_domain
        assert self.validator(self.form_mock, self.field_mock) is None

    @pytest.mark.parametrize("new_buyer_domain", (
        "br.com",
        "org.uk",
        "ORG.UK",
        "uk",
        ".me",
    ))
    def test_failure(self, new_buyer_domain):
        self.field_mock.data = new_buyer_domain
        with pytest.raises(ValidationError, match=new_buyer_domain.lower()):
            self.validator(self.form_mock, self.field_mock)
