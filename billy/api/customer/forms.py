from __future__ import unicode_literals

from wtforms import Form
from wtforms import TextField
from wtforms import validators


class CustomerCreateForm(Form):
    external_id = TextField('External ID', [
        validators.Optional(),
    ])
