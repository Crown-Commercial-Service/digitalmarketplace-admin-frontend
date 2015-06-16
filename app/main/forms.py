from flask_wtf import Form
from wtforms import StringField, DateField
from wtforms.validators import DataRequired, Optional, Regexp


class FilterAuditEventsForm(Form):
    audit_date = DateField(
        'Audit Date',
        format='%Y-%m-%d',
        validators=[Optional()])
    acknowledged = StringField(
        'acknowledged',
        default="all",
        validators=[
            Regexp('^(all|acknowledged|not-acknowledged)$'),
            DataRequired()]
    )
