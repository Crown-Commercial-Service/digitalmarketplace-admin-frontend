from bisect import bisect_left
from itertools import chain
from pathlib import Path
import typing

from dmutils.forms.fields import DMRadioField, DMStripWhitespaceStringField

from flask import current_app
from flask_wtf import FlaskForm
from wtforms import validators, RadioField
from wtforms.validators import DataRequired, AnyOf, InputRequired, Length, Optional, Regexp, ValidationError

from .. import data_api_client
from .helpers.countries import COUNTRY_TUPLE

ADMIN_ROLES = [
    {
        "value": 'admin-framework-manager',
        "label": 'Manage framework applications',
        "description": 'Manages communications about the framework and publishes supplier clarification questions.',
    },
    {
        "value": 'admin-ccs-sourcing',
        "label": 'Audit framework applications (CCS Sourcing)',
        "description": 'Checks declarations and agreements.',
    },
    {
        "value": 'admin-ccs-category',
        "label": 'Manage services (CCS Category)',
        "description": 'Helps with service problems and makes sure services are in scope.',
    },
    {
        "value": 'admin-ccs-data-controller',
        "label": 'Manage data (CCS Data Controller)',
        "description": 'Helps create consistent supplier data and updates company details.',
    },
    {
        "value": 'admin',
        "label": 'Support user accounts',
        "description": 'Helps buyers and suppliers solve problems with their accounts.'
    },
]


class AdminEmailAddressValidator(object):
    def __init__(self, message=None):
        self.message = message

    def __call__(self, form, field):
        if not data_api_client.email_is_valid_for_admin_user(field.data):
            raise validators.StopValidation(self.message)


class UserAccountDoesntAlreadyExistValidator(object):
    def __init__(self, message=None):
        self.message = message

    def __call__(self, form, field):
        if data_api_client.get_user(email_address=field.data) is not None:
            raise validators.StopValidation(self.message)


class EmailAddressForm(FlaskForm):
    email_address = DMStripWhitespaceStringField(
        "Email address",
        hint="Enter the email address of the person you wish to invite",
        validators=[
            validators.DataRequired(message="Email can not be empty"),
            validators.Email(message="Please enter a valid email address"),
        ])


class MoveUserForm(FlaskForm):
    user_to_move_email_address = DMStripWhitespaceStringField(
        "Move an existing user to this supplier",
        hint="Enter the email address of the existing user you wish to move to this supplier",
        validators=[
            validators.DataRequired(message="Email can not be empty"),
            validators.Email(message="Please enter a valid email address"),
        ])


class NotInDomainSuffixBlacklistValidator:
    "WTForms validator, asserting that supplied value is not a prefix of any of the values present in a blacklist"

    # path, relative to flask app root_path, to look for suffix blacklist files. all files found here will be read,
    # one suffix per line
    BLACKLIST_DIR_PATH: str = "data/public_domain_suffix_blacklist"

    @staticmethod
    def _normalized_suffix(suffix: str) -> str:
        """Reverses suffix and ensures last character is a '.'

        * Reverses suffix because sorting of strings works by prefix, we want to search by suffix
        * Adds "." because all suffixes we deal with implicitly begin with a separator, we need to make that
            explicit for lookup
        """
        return (("" if suffix.startswith(".") else ".") + suffix.strip().lower())[::-1]

    @staticmethod
    def _un_normalized_suffix(normalized_suffix: str) -> str:
        # we can't fully reverse the normalization process as it throws information away, but we can restore its
        # presentational sanity.
        return normalized_suffix[::-1]

    @classmethod
    def _lines_from_filepath(cls, filepath: Path) -> typing.Sequence[str]:
        with filepath.open("r", encoding="utf-8") as f:
            return tuple(cls._normalized_suffix(line) for line in f if line)

    # this value is not populated until first access because construction depends on current_app being available
    _blacklist: typing.Optional[typing.Sequence[str]] = None

    @classmethod
    def get_blacklist(cls) -> typing.Sequence[str]:
        """Loads and caches the blacklist on the class."""
        if cls._blacklist is None:
            cls._blacklist = tuple(sorted(chain.from_iterable(
                cls._lines_from_filepath(filepath)
                for filepath in (Path(current_app.root_path) / cls.BLACKLIST_DIR_PATH).iterdir()
                if filepath.is_file()
            )))
        return cls._blacklist

    def __init__(self, message):
        self.message = message

    def __call__(self, form, field) -> None:
        """Validate that the provided field is not in our domain suffix blacklist.

        Use bisect_left to find the index of where the provided suffix would be inserted in our sorted blacklist and
        check if the string that is already at that index matches the provided suffix. Ie the provided suffix is already
        in the list.
        """
        blacklist = self.get_blacklist()
        suffix = self._normalized_suffix(field.data)
        insertion_index = bisect_left(blacklist, suffix)
        if insertion_index < len(blacklist) and blacklist[insertion_index].startswith(suffix):
            raise ValidationError(
                self.message % {"matched_suffix": self._un_normalized_suffix(blacklist[insertion_index])}
            )


class EmailDomainForm(FlaskForm):
    new_buyer_domain = DMStripWhitespaceStringField(
        "Add a buyer email domain",
        hint="For example, police.uk",
        validators=[
            validators.DataRequired(message="The domain field can not be empty."),
            NotInDomainSuffixBlacklistValidator(
                message="Cannot use this domain suffix: ‘%(matched_suffix)s’ domains are publicly purchasable"
            ),
        ],
    )


class InviteAdminForm(FlaskForm):

    email_address = DMStripWhitespaceStringField(
        "Email address",
        validators=[
            validators.DataRequired(message='You must provide an email address'),
            validators.Email(message='Please enter a valid email address'),
            AdminEmailAddressValidator(message='The email address must belong to an approved domain'),
            UserAccountDoesntAlreadyExistValidator("This email address already has a user account associated with it"),
        ]
    )
    role = DMRadioField(
        "Permissions",
        validators=[
            validators.InputRequired(message='You must choose a permission')
        ],
        options=ADMIN_ROLES,
    )


class EditAdminUserForm(FlaskForm):
    edit_admin_name = DMStripWhitespaceStringField('Name', validators=[
        DataRequired(message="You must provide a name.")
    ])

    edit_admin_permissions = DMRadioField(
        'Permissions',
        options=ADMIN_ROLES,
    )

    status_choices = [
        ("True", "Active"),
        ("False", "Suspended"),
    ]

    edit_admin_status = DMRadioField('Status', choices=status_choices)


# Supplier details forms

class EditSupplierRegisteredAddressForm(FlaskForm):
    street = DMStripWhitespaceStringField("Building and street", validators=[
        InputRequired(message="You need to enter the street address."),
        Length(max=255, message="You must provide a building and street name under 256 characters."),
    ])
    city = DMStripWhitespaceStringField("Town or city", validators=[
        InputRequired(message="You need to enter the town or city."),
        Length(max=255, message="You must provide a town or city name under 256 characters."),
    ])
    postcode = DMStripWhitespaceStringField("Postcode", validators=[
        InputRequired(message="You need to enter the postcode."),
        Length(max=15, message="You must provide a valid postcode under 15 characters."),
    ])
    country = DMStripWhitespaceStringField("Country", validators=[
        InputRequired(message="You need to enter a country."),
        AnyOf(values=[country[1] for country in COUNTRY_TUPLE], message="You must enter a valid country."),
    ])

    def validate(self):
        # If a user is trying to change the country and enters an invalid option (blank or not a country),
        # and submits the form, the country field is not submitted with the form.
        # The old value will be re-populated in the field (with the validation error message).
        # This could be confusing if there are multiple fields with errors, so clear the field for now.
        if not self.country.raw_data:
            self.country.data = ''
        return super(EditSupplierRegisteredAddressForm, self).validate()


class EditSupplierRegisteredNameForm(FlaskForm):
    registered_company_name = DMStripWhitespaceStringField('Registered company name', validators=[
        InputRequired(message="You must provide a registered company name."),
        Length(max=255, message="You must provide a registered company name under 256 characters.")
    ])


class EditSupplierCompanyRegistrationNumberForm(FlaskForm):
    companies_house_number = DMStripWhitespaceStringField(
        'Companies House number',
        default='',
        validators=[
            Optional(),
            Regexp(r'^([0-9]{2}|[A-Za-z]{2})[0-9]{6}$',
                   message="You must provide a valid 8 character Companies House number."
                   )
        ]
    )
    other_company_registration_number = DMStripWhitespaceStringField(
        'Other company registration number',
        default='',
        validators=[
            Optional(),
            Length(max=255, message="You must provide a registration number under 256 characters.")
        ]
    )

    def validate(self):
        # Admin must supply one or other field
        # Admin cannot supply both fields
        valid = True
        if not super(EditSupplierCompanyRegistrationNumberForm, self).validate():
            valid = False

        if self.other_company_registration_number.data and self.companies_house_number.data:
            self.companies_house_number.errors.append(
                'You must provide only one of either a Companies House number or overseas registration number.'
            )
            valid = False

        if not self.companies_house_number.data and not self.other_company_registration_number.data:
            self.companies_house_number.errors.append('You must provide an answer.')
            valid = False

        return valid


class EditFrameworkStatusForm(FlaskForm):

    status = RadioField(
        id="input-status-1",  # TODO: change to input-copy_service when on govuk-frontend~3
        label="Framework status",
        description="Tell the rest of the team before making a change",
        validators=[
            validators.InputRequired(message='You must choose a framework status')
        ],
        choices=[
            (status, status.capitalize())
            for status in ('coming', 'open', 'pending', 'standstill', 'live', 'expired')
        ],
    )

    def items(self):
        return [
            {"value": value, "text": label, "checked": checked}
            for value, label, checked in self.status.iter_choices()
        ]
