from dmutils.forms.fields import DMRadioField, DMStripWhitespaceStringField
from flask_wtf import FlaskForm
from wtforms import validators
from wtforms.validators import DataRequired

from .. import data_api_client

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


class EmailDomainForm(FlaskForm):
    new_buyer_domain = DMStripWhitespaceStringField(
        "Add a buyer email domain",
        hint="For example, police.uk",
        validators=[
            validators.DataRequired(message="The domain field can not be empty.")
        ])


class InviteAdminForm(FlaskForm):

    email_address = DMStripWhitespaceStringField(
        "Email address",
        validators=[
            validators.DataRequired(message='You must provide an email address'),
            validators.Email(message='Please enter a valid email address'),
            AdminEmailAddressValidator(message='The email address must belong to an approved domain')
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
