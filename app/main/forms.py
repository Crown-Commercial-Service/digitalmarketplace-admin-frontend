from flask_wtf import Form
from wtforms import StringField, DateField
from wtforms.validators import DataRequired, Optional, Regexp
from datetime import datetime


class ServiceUpdateAuditEventsForm(Form):
    audit_date = DateField(
        'Audit Date',
        format='%Y-%m-%d',
        validators=[Optional()])
    acknowledged = StringField(
        'acknowledged',
        default="false",
        validators=[
            Regexp('^(all|true|false)$'),
            Optional()]
    )

    def default_acknowledged(self):
        if self.acknowledged.data:
            return self.acknowledged.data
        else:
            return self.acknowledged.default

    def format_date(self):
        if self.audit_date.data:
            return datetime.strftime(self.audit_date.data, '%Y-%m-%d')
        else:
            return None

    def format_date_for_display(self):
        if self.audit_date.data:
            return datetime.strftime(self.audit_date.data, '%d/%m/%Y')
        else:
            return datetime.now().strftime("%d/%m/%Y")
