from __future__ import unicode_literals

from wtforms import Form
from wtforms import TextField
from wtforms import IntegerField
from wtforms import validators

from billy.models.customer import CustomerModel
from billy.api.utils import RecordExistValidator
from billy.api.utils import MINIMUM_AMOUNT


class InvoiceCreateForm(Form):
    customer_guid = TextField('Customer GUID', [
        validators.Required(),
        RecordExistValidator(CustomerModel),
    ])
    amount = IntegerField('Amount', [
        validators.Required(),
        # TODO: what is the minimum amount limitation we have?
        validators.NumberRange(min=MINIMUM_AMOUNT)
    ])
    payment_uri = TextField('Payment URI', [
        validators.Optional(),
    ])

    # TODO: items
