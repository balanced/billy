from __future__ import unicode_literals

from wtforms import Form
from wtforms import TextField
from wtforms import IntegerField
from wtforms import validators

from billy.models.customer import CustomerModel
from billy.api.utils import RecordExistValidator
from billy.api.utils import STATEMENT_REXP 
#from billy.api.utils import MINIMUM_AMOUNT


class InvoiceCreateForm(Form):
    customer_guid = TextField('Customer GUID', [
        validators.Required(),
        RecordExistValidator(CustomerModel),
    ])
    amount = IntegerField('Amount', [
        validators.Required(),
        #validators.NumberRange(min=MINIMUM_AMOUNT)
    ])
    payment_uri = TextField('Payment URI', [
        validators.Optional(),
    ])
    title = TextField('Title', [
        validators.Optional(),
        validators.Length(max=128),
    ])
    external_id = TextField('External ID', [
        validators.Optional(),
    ])
    appears_on_statement_as = TextField('Appears on statement as', [
        validators.Optional(),
        validators.Regexp(STATEMENT_REXP),
        validators.Length(max=18),
    ])
    # TODO: items


class InvoiceUpdateForm(Form):
    payment_uri = TextField('Payment URI', [
        validators.Optional(),
    ])
    title = TextField('Title', [
        validators.Optional(),
        validators.Length(max=128),
    ])
    # TODO: items
