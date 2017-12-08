from wtforms import RadioField, validators
from flask.ext.wtf import Form
from wtforms.validators import DataRequired
from dmutils.forms import StripWhitespaceStringField

from .. import data_api_client


ADMIN_ROLES = [
    (
        'admin-framework-manager',
        'Manage framework applications',
        'Manages communications about the framework and publishes supplier clarification questions.',
    ),
    (
        'admin-ccs-sourcing',
        'Audit framework applications (CCS Sourcing)',
        'Checks declarations and agreements.',
    ),
    (
        'admin-ccs-category',
        'Manage services (CCS Category)',
        'Helps with service problems and makes sure services are in scope.',
    ),
    (
        'admin',
        'Support user accounts',
        'Helps buyers and suppliers solve problems with their accounts.'
    ),
]


class AdminEmailAddressValidator(object):

    def __init__(self, message=None):
        self.message = message

    def __call__(self, form, field):
        if not data_api_client.email_is_valid_for_admin_user(field.data):
            raise validators.StopValidation(self.message)


class EmailAddressForm(Form):
    email_address = StripWhitespaceStringField('Email address', validators=[
        validators.DataRequired(message="Email can not be empty"),
        validators.Email(message="Please enter a valid email address")
    ])


class MoveUserForm(Form):
    user_to_move_email_address = StripWhitespaceStringField('Move an existing user to this supplier', validators=[
        validators.DataRequired(message="Email can not be empty"),
        validators.Email(message="Please enter a valid email address")
    ])


class EmailDomainForm(Form):
    new_buyer_domain = StripWhitespaceStringField('Add a buyer email domain', validators=[
        validators.DataRequired(message="The domain field can not be empty.")
    ])


class InviteAdminForm(Form):

    email_address = StripWhitespaceStringField(
        'Email address',
        validators=[
            validators.DataRequired(message='You must provide an email address'),
            validators.Email(message='Please enter a valid email address'),
            AdminEmailAddressValidator(message='The email address must belong to an approved domain')
        ]
    )
    role = RadioField(
        'Permissions',
        validators=[validators.InputRequired(message='You must choose a permission')],
        choices=[(code, name) for code, name, description in ADMIN_ROLES]
    )

    def __init__(self, *args, **kwargs):
        super(InviteAdminForm, self).__init__(*args, **kwargs)
        self.role.toolkit_macro_options = [
            {
                'value': choice[0],
                'label': choice[1],
                'description': choice[2]
            } for choice in ADMIN_ROLES
        ]


class EditAdminUserForm(Form):
    edit_admin_name = StripWhitespaceStringField('Name', validators=[
        DataRequired(message="You must provide a name.")
    ])

    edit_admin_permissions = RadioField(
        'Permissions',
        choices=[(code, name) for code, name, description in ADMIN_ROLES]
    )

    status_choices = [
        ("True", "Active"),
        ("False", "Suspended"),
    ]

    edit_admin_status = RadioField('Status', choices=status_choices)

    def __init__(self, *args, **kwargs):
        super(EditAdminUserForm, self).__init__(*args, **kwargs)
        self.edit_admin_permissions.toolkit_macro_options = [
            {
                'value': choice[0],
                'label': choice[1],
                'description': choice[2]
            } for choice in ADMIN_ROLES
        ]
        self.edit_admin_status.toolkit_macro_options = [
            {'value': choice[0], 'label': choice[1]} for choice in self.status_choices
        ]
