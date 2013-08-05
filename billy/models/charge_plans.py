from __future__ import unicode_literals
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (Column, Unicode, Integer, Boolean, DateTime,
                        ForeignKey, UniqueConstraint, CheckConstraint)
from sqlalchemy.orm import relationship

from models import Base, Company, ChargeSubscription
from models.base import RelativeDelta
from utils.generic import uuid_factory


class ChargePlan(Base):
    __tablename__ = 'charge_plans'

    guid = Column(Unicode, primary_key=True, default=uuid_factory('PL'))
    external_id = Column(Unicode, nullable=False)
    company_id = Column(Unicode, ForeignKey(Company.guid), nullable=False)
    name = Column(Unicode, nullable=False)
    price_cents = Column(Integer, CheckConstraint('price_cents >= 0'),
                         nullable=False)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    deleted_at = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.utcnow)
    trial_interval = Column(RelativeDelta)
    plan_interval = Column(RelativeDelta)

    subscriptions = relationship('ChargeSubscription', backref='charge_plan',
                                 cascade='delete')

    __table_args__ = (UniqueConstraint(external_id, company_id,
                                       name='plan_id_company_unique'),
                      )

    def update(self, name):
        """
        Updates the name of a plan
        """
        self.name = name
        self.updated_at = datetime.utcnow()
        self.session.commit()
        return self

    def disable(self):
        """
        Disables a charge plan. Does not effect current subscribers.
        """
        self.active = False
        self.updated_at = datetime.utcnow()
        self.deleted_at = datetime.utcnow()
        self.session.commit()
        return self

    def subscribe(self, customer, quantity=1,
                  charge_at_period_end=False, start_dt=None):
        """
        Subscribe a customer to a plan
        """
        from models import ChargePlanInvoice

        current_coupon = customer.coupon
        start_date = start_dt or datetime.utcnow()
        due_on = start_date
        can_trial = self.can_customer_trial(customer)
        end_date = start_date + self.plan_interval
        if can_trial and self.trial_interval:
            end_date += self.trial_interval
            due_on += self.trial_interval
        if charge_at_period_end:
            due_on = end_date
        amount_base = self.price_cents * Decimal(quantity)
        amount_after_coupon = amount_base
        coupon_id = current_coupon.guid if current_coupon else None
        if self.current_coupon and current_coupon:
            dollars_off = current_coupon.price_off_cents
            percent_off = current_coupon.percent_off_int
            amount_after_coupon -= dollars_off  # BOTH CENTS, safe
            amount_after_coupon -= int(
                amount_after_coupon * Decimal(percent_off) / Decimal(100))
        balance = amount_after_coupon
        new_sub = ChargeSubscription.create_or_activate(customer, self)
        ChargePlanInvoice.prorate_last(customer, self)
        pi = ChargePlanInvoice.create(
            subscription_id=new_sub.guid,
            relevant_coupon=coupon_id,
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
        try:
            self.session.commit()
        except:
            self.session.rollback()
            raise
        return pi

    def unsubscribe(self, customer, cancel_at_period_end=False):

        from models import ChargePlanInvoice, ChargeSubscription

        if cancel_at_period_end:
            result = ChargeSubscription.query.filter(
                ChargeSubscription.customer_id == customer.guid,
                ChargeSubscription.plan_id == self.guid,
                ChargeSubscription.is_active == True).one()
            result.is_active = False
            self.session.commit()
        else:
            return ChargePlanInvoice.prorate_last(customer, self)
        return True

    def can_customer_trial(self, customer):
        """
        Whether a customer can trial a charge plan
        """
        count = ChargeSubscription.query.filter(
            ChargeSubscription.customer_id == customer.guid,
            ChargeSubscription.plan_id == self.guid
        ).count()
        return not bool(count)
