from flask_wtf import Form
from wtforms import StringField, DateField, PasswordField, IntegerField
from wtforms.validators import Optional, AnyOf, DataRequired, \
    Email
from datetime import datetime
from dmutils.formats import DATE_FORMAT
from dmutils.forms import StripWhitespaceStringField


class ServiceUpdateAuditEventsForm(Form):
    audit_date = DateField(
        'Audit Date',
        format=DATE_FORMAT,
        validators=[Optional()])
    acknowledged = StringField(
        'acknowledged',
        default="false",
        validators=[
            AnyOf(['all', 'true', 'false']),
            Optional()]
    )
    page = IntegerField(
        default=1,
        validators=[
            Optional()
        ]
    )

    def default_acknowledged(self):
        if self.acknowledged.data:
            return self.acknowledged.data
        else:
            return self.acknowledged.default

    def format_date(self):
        if self.audit_date.data:
            return datetime.strftime(self.audit_date.data, DATE_FORMAT)
        else:
            return None

    def format_date_for_display(self):
        if self.audit_date.data:
            return self.audit_date.data
        else:
            return datetime.utcnow()


class LoginForm(Form):
    email_address = StripWhitespaceStringField('Email address', validators=[
        DataRequired(message='Email cannot be empty'),
        Email(message='Please enter a valid email address')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Please enter your password')
    ])


class EmailAddressForm(Form):
    email_address = StripWhitespaceStringField('Email address', validators=[
        DataRequired(message="Email can not be empty"),
        Email(message="Please enter a valid email address")
    ])


class MoveUserForm(Form):
    user_to_move_email_address = StripWhitespaceStringField('Move an existing user to this supplier', validators=[
        DataRequired(message="Email can not be empty"),
        Email(message="Please enter a valid email address")
    ])
