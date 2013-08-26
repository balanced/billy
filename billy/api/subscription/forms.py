from __future__ import unicode_literals

import pytz
import iso8601
from wtforms import Form
from wtforms import TextField
from wtforms import DecimalField
from wtforms import Field
from wtforms import validators

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


class SubscriptionCreateForm(Form):
    customer_guid = TextField('Customer GUID', [
        validators.Required(),
        RecordExistValidator(CustomerModel),
    ])
    plan_guid = TextField('Plan GUID', [
        validators.Required(),
        RecordExistValidator(PlanModel),
    ])
    amount = DecimalField('Amount', [
        validators.Optional(),
        # TODO: what is the minimum amount limitation we have?
        validators.NumberRange(min=0.01)
    ])
    started_at = ISO8601Field('Started at datetime', [
        validators.Optional(),
    ])
