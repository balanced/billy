from __future__ import unicode_literals

from sqlalchemy.orm.exc import *
from wtforms import (
    Form, TextField, IntegerField, validators, DateTimeField, BooleanField)

from api.errors import BillyExc
from models import Customer, ChargePlan, ChargeSubscription


class PlanSubCreateForm(Form):
    customer_id = TextField('Customer ID', [validators.Required(),
                                            validators.Length(min=5, max=150)])
    plan_id = TextField('ChargePlan ID', [validators.Required(),
                                    validators.Length(min=5, max=150)])

    quantity = IntegerField('Quantity', default=1)

    charge_at_period_end = BooleanField('Charge at period end?', default=False)

    start_dt = DateTimeField('Start Datetime', default=None)

    def save(self, group_obj):
        try:
            customer = Customer.retrieve(self.customer_id.data, group_obj.id)
            if not customer:
                raise BillyExc['404_CUSTOMER_NOT_FOUND']
            plan = ChargePlan.retrieve(self.plan_id.data, group_obj.id)
            if not plan:
                raise BillyExc['404_PLAN_NOT_FOUND']
            return ChargeSubscription.subscribe(customer, plan,
                                              quantity=self.quantity.data,
                                              charge_at_period_end=self.charge_at_period_end.data,
                                              start_dt=self.start_dt.data).subscription
        except ValueError, e:
            raise BillyExc[e.message]


class PlanSubDeleteForm(Form):
    customer_id = TextField('Customer ID', [validators.Required(),
                                            validators.Length(min=5, max=150)])
    plan_id = TextField('ChargePlan ID', [validators.Required(),
                                    validators.Length(min=5, max=150)])

    cancel_at_period_end = BooleanField('Cancel at period end?', default=False)

    def save(self, group_obj):
        try:
            customer = Customer.retrieve(self.customer_id.data, group_obj.id)
            if not customer:
                raise BillyExc['404_CUSTOMER_NOT_FOUND']
            plan = ChargePlan.retrieve(self.plan_id.data, group_obj.id)
            if not plan:
                raise BillyExc['404_PLAN_NOT_FOUND']
            return ChargeSubscription.unsubscribe(customer, plan,
                                                cancel_at_period_end=self.cancel_at_period_end.data).subscription
        except NoResultFound:
            raise BillyExc['404_PLAN_SUB_NOT_FOUND']
        except ValueError, e:
            raise BillyExc[e.message]
