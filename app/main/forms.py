from flask_wtf import Form
from wtforms import PasswordField
from wtforms.validators import DataRequired, Email
from dmutils.forms import StripWhitespaceStringField


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
