from __future__ import unicode_literals

from wtforms import Form
from wtforms import TextField
from wtforms import validators


class CustomerCreateForm(Form):
    processor_uri = TextField('URI of customer in processor', [
        validators.Optional(),
    ])
