from __future__ import unicode_literals

from sqlalchemy.exc import *
from wtforms import (Form, TextField, IntegerField, validators, ValidationError,
                     DateTimeField)

from models import Plan
from api.errors import BillyExc


class PlanCreateForm(Form):
    plan_id = TextField('Plan ID',
                          [validators.Required(),
                           validators.Length(min=5, max=150)])
    name = TextField('Name',
                     [validators.Required(),
                      validators.Length(min=3, max=150)])

    price_cents = IntegerField('Price Cents', [validators.Required()])

    plan_interval = IntegerField('Plan Interval')

    trial_interval = IntegerField('Trial Interval')

    def save(self, group_obj):
        try:
            return Plan.create(external_id=self.plan_id.data,
                                   group_id=group_obj.guid,
                                   name=self.name.data,
                                   price_cents=self.price_cents.data,
                                   plan_interval=self.plan_interval.data,
                                   trial_interval=self.trial_interval.data,
            )
        except IntegrityError:
            raise BillyExc['409_PLAN_ALREADY_EXISTS']
        except ValueError, e:
            raise BillyExc[e.message]
