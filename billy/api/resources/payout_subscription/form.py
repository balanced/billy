from __future__ import unicode_literals

from sqlalchemy.orm.exc import *
from wtforms import (
    Form, TextField, IntegerField, validators, DateTimeField, BooleanField)

from api.errors import BillyExc
from models import Customer, PayoutPlan, PayoutSubscription


class PayoutSubCreateForm(Form):
    customer_id = TextField('Customer ID', [validators.Required(),
                                            validators.Length(min=5, max=150)])
    payout_id = TextField('PayoutPlan ID', [validators.Required(),
                                        validators.Length(min=5, max=150)])

    first_now = BooleanField('Charge at period end?', default=False)

    start_dt = DateTimeField('Start Datetime', default=None)

    def save(self, group_obj):
        try:
            customer = Customer.retrieve(self.customer_id.data, group_obj.id)
            if not customer:
                raise BillyExc['404_CUSTOMER_NOT_FOUND']
            payout = PayoutPlan.retrieve(self.payout_id.data, group_obj.id)
            if not payout:
                raise BillyExc['404_PAYOUT_NOT_FOUND']
            return PayoutSubscription.subscribe(customer, payout,
                                                first_now=self.first_now.data,
                                                start_dt=self.start_dt.data)\
                .subscription
        except ValueError, e:
            raise BillyExc[e.message]


class PayoutSubDeleteForm(Form):
    customer_id = TextField('Customer ID', [validators.Required(),
                                            validators.Length(min=5, max=150)])
    payout_id = TextField('PayoutPlan ID', [validators.Required(),
                                        validators.Length(min=5, max=150)])

    cancel_scheduled = BooleanField('Cancel scheduled?', default=False)

    def save(self, group_obj):
        try:
            customer = Customer.retrieve(self.customer_id.data, group_obj.id)
            if not customer:
                raise BillyExc['404_CUSTOMER_NOT_FOUND']
            payout = PayoutPlan.retrieve(self.payout_id.data, group_obj.id)
            if not payout:
                raise BillyExc['404_PLAN_NOT_FOUND']
            return PayoutSubscription.unsubscribe(customer, payout,
                                                  cancel_scheduled=self
                                                  .cancel_scheduled.data)\
                .subscription
        except NoResultFound:
            raise BillyExc['404_PLAN_SUB_NOT_FOUND']
        except ValueError, e:
            raise BillyExc[e.message]
