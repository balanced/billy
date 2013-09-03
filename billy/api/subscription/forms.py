from __future__ import unicode_literals

import pytz
import iso8601
from wtforms import Form
from wtforms import TextField
from wtforms import DecimalField
from wtforms import Field
from wtforms import validators

from billy.models import tables
from billy.models.customer import CustomerModel
from billy.models.plan import PlanModel
from billy.api.utils import RecordExistValidator


class ISO8601Field(Field):
    """This filed validates and converts input ISO8601 into UTC naive 
    datetime

    """

    def process_formdata(self, valuelist):
        if not valuelist:
            return
        try:
            self.data = iso8601.parse_date(valuelist[0])
        except iso8601.ParseError:
            raise ValueError(self.gettext('Invalid ISO8601 datetime {}')
                             .format(valuelist[0]))
        self.data = self.data.astimezone(pytz.utc)
        self.data = self.data.replace(tzinfo=None)


class NoPastValidator(object):
    """Make sure a datetime is not in past

    """

    def __init__(self, now_func=tables.now_func):
        self.now_func = now_func

    def __call__(self, form, field):
        if not field.data:
            return
        now = self.now_func()
        if field.data < now:
            msg = field.gettext('Datetime {} in the past is not allowed'
                                .format(field.data))
            raise ValueError(msg)


class SubscriptionCreateForm(Form):
    customer_guid = TextField('Customer GUID', [
        validators.Required(),
        RecordExistValidator(CustomerModel),
    ])
    plan_guid = TextField('Plan GUID', [
        validators.Required(),
        RecordExistValidator(PlanModel),
    ])
    payment_uri = TextField('Payment URI', [
        validators.Optional(),
    ])
    amount = DecimalField('Amount', [
        validators.Optional(),
        # TODO: what is the minimum amount limitation we have?
        validators.NumberRange(min=0.01)
    ])
    started_at = ISO8601Field('Started at datetime', [
        validators.Optional(),
        NoPastValidator(),
    ])
