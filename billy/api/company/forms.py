from __future__ import unicode_literals

from wtforms import Form
from wtforms import TextField
from wtforms import validators


class CompanyCreateForm(Form):
    processor_key = TextField('Processor key', [
        validators.Required(),
    ])
