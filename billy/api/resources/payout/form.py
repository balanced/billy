from __future__ import unicode_literals

from sqlalchemy.exc import *
from wtforms import (Form, TextField, IntegerField, validators)

from api.errors import BillyExc
from models import PayoutPlan
from utils.intervals import interval_matcher


class PayoutCreateForm(Form):
    payout_id = TextField('PayoutPlan ID', [validators.Required(),
                                        validators.Length(min=5, max=150)])
    name = TextField('Name',
                     [validators.Required(),
                      validators.Length(min=3, max=150)])

    balance_to_keep_cents = IntegerField('Balance to Keep Cents',
                                         [validators.Required()])

    payout_interval = TextField('PayoutPlan Interval', [validators.Required()])

    def validate_balance_to_keep(self, key, address):
        if not address > 0:
            raise ValueError("400_BALANCE_TO_KEEP_CENTS")
        return address


    def save(self, group_obj):
        try:
            try:
                payout_int = interval_matcher(self.payout_interval.data)
            except ValueError:
                raise BillyExc['400_PAYOUT_INTERVAL']
            return PayoutPlan.create(your_id=self.payout_id.data,
                                 group_id=group_obj.id,
                                 name=self.name.data,
                                 balance_to_keep_cents=self
                                 .balance_to_keep_cents.data,
                                 payout_interval=payout_int,
                                 )
        except IntegrityError:
            raise BillyExc['409_PAYOUT_ALREADY_EXISTS']
        except ValueError, e:
            raise BillyExc[e.message]


class PayoutUpdateForm(Form):
    name = TextField('Name', [validators.Length(min=3, max=150)], default=None)

    def save(self, payout):
        if self.name:
            return payout.update(self.name.data)
        return payout
