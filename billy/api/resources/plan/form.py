from __future__ import unicode_literals

from sqlalchemy.exc import *
from wtforms import (Form, TextField, IntegerField, validators)

from billy.api.errors import BillyExc
from billy.models import ChargePlan
from billy.utils.intervals import interval_matcher


class PlanCreateForm(Form):
    plan_id = TextField('ChargePlan ID', [validators.Required(),
                                    validators.Length(min=5, max=150)])
    name = TextField('Name',
                     [validators.Required(),
                      validators.Length(min=3, max=150)])

    price_cents = IntegerField('Price Cents', [validators.Required()])

    plan_interval = TextField('ChargePlan Interval', [validators.Required()])

    trial_interval = TextField('Trial Interval', default=None)

    def validate_price_cents(self, key, address):
        if not address > 0:
            raise ValueError("400_PRICE_CENTS")
        return address

    def save(self, group_obj):
        try:
            try:
                if self.trial_interval.data:
                    trial_int = interval_matcher(self.trial_interval.data)
                else:
                    trial_int = None
            except ValueError:
                raise BillyExc['400_TRIAL_INTERVAL']
            try:
                plan_int = interval_matcher(self.plan_interval.data)
            except ValueError:
                raise BillyExc['400_PLAN_INTERVAL']
            return ChargePlan.create(your_id=self.plan_id.data,
                               group_id=group_obj.id,
                               name=self.name.data,
                               price_cents=self.price_cents.data,
                               plan_interval=plan_int,
                               trial_interval=trial_int,
                               )
        except IntegrityError:
            raise BillyExc['409_PLAN_ALREADY_EXISTS']
        except ValueError, e:
            raise BillyExc[e.message]


class PlanUpdateForm(Form):
    name = TextField('Name', [validators.Length(min=3, max=150)], default=None)

    def save(self, plan):
        if self.name:
            return plan.update(self.name.data)
        return plan
