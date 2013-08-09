from __future__ import unicode_literals
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (Column, Unicode, Integer, Boolean, DateTime,
                        ForeignKey, UniqueConstraint, CheckConstraint)
from sqlalchemy.orm import relationship

from models import Base, ChargeSubscription, ChargePlanInvoice
from models.base import RelativeDelta
from utils.models import uuid_factory


class ChargePlan(Base):
    __tablename__ = 'charge_plans'

    id = Column(Unicode, primary_key=True, default=uuid_factory('CP'))
    your_id = Column(Unicode, nullable=False)
    company_id = Column(Unicode, ForeignKey('companies.id', ondelete='cascade'),
                        nullable=False)
    name = Column(Unicode, nullable=False)
    price_cents = Column(Integer, CheckConstraint('price_cents >= 0'),
                         nullable=False)
    active = Column(Boolean, default=True)
    disabled_at = Column(DateTime)
    trial_interval = Column(RelativeDelta)
    plan_interval = Column(RelativeDelta)

    subscriptions = relationship('ChargeSubscription', backref='plan',
                                 cascade='delete, delete-orphan')

    __table_args__ = (UniqueConstraint(your_id, company_id,
                                       name='plan_id_company_unique'),
    )

    def subscribe(self, customer, quantity=1,
                  charge_at_period_end=False, start_dt=None, coupon=None):
        """
        Subscribe a customer to a plan
        """
        can_trial = self.can_customer_trial(customer)
        subscription = ChargeSubscription.create(customer, self, coupon=coupon)
        coupon = subscription.coupon
        start_date = start_dt or datetime.utcnow()
        due_on = start_date
        end_date = start_date + self.plan_interval
        if can_trial and self.trial_interval:
            end_date += self.trial_interval
            due_on += self.trial_interval
        if charge_at_period_end:
            due_on = end_date
        amount_base = self.price_cents * Decimal(quantity)
        amount_after_coupon = amount_base

        if subscription.coupon:
            dollars_off = coupon.price_off_cents
            percent_off = coupon.percent_off_int
            amount_after_coupon -= dollars_off  # BOTH CENTS, safe
            amount_after_coupon -= int(
                amount_after_coupon * Decimal(percent_off) / Decimal(100))
        balance = amount_after_coupon
        ChargePlanInvoice.prorate_last(customer, self)
        ChargePlanInvoice.create(
            subscription=subscription,
            coupon=subscription.coupon,
            start_dt=start_date,
            end_dt=end_date,
            due_dt=due_on,
            amount_base_cents=amount_base,
            amount_after_coupon_cents=amount_after_coupon,
            amount_paid_cents=0,
            remaining_balance_cents=balance,
            quantity=quantity,
            charge_at_period_end=charge_at_period_end,
            includes_trial=can_trial
        )
        return subscription

    def disable(self):
        """
        Disables a charge plan. Does not effect current subscribers.
        """
        self.active = False
        self.disabled_at = datetime.utcnow()
        return self

    def can_customer_trial(self, customer):
        """
        Whether a customer can trial a charge plan
        """
        return not ChargeSubscription.query.filter(
            ChargeSubscription.customer == customer,
            ChargeSubscription.plan == self
        ).first()
