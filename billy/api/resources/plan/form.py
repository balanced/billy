from __future__ import unicode_literals

from sqlalchemy.exc import *
from wtforms import (Form, TextField, IntegerField, validators)

from api.errors import BillyExc
from models import Plan
from utils.intervals import interval_matcher


class PlanCreateForm(Form):
    plan_id = TextField('Plan ID', [validators.Required(),
                                    validators.Length(min=5, max=150)])
    name = TextField('Name',
                     [validators.Required(),
                      validators.Length(min=3, max=150)])

    price_cents = IntegerField('Price Cents', [validators.Required()])

    plan_interval = TextField('Plan Interval', [validators.Required()])

    trial_interval = TextField('Trial Interval', default=None)


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
            return Plan.create(external_id=self.plan_id.data,
                               group_id=group_obj.guid,
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