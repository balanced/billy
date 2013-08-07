from __future__ import unicode_literals
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (Column, Unicode, ForeignKey, DateTime, Boolean,
                        Integer, CheckConstraint)
from sqlalchemy.orm import relationship, backref

from models import Base, ChargeSubscription
from utils.models import uuid_factory


class ChargePlanInvoice(Base):
    __tablename__ = 'charge_plan_invoices'

    id = Column(Unicode, primary_key=True, default=uuid_factory('CPI'))
    subscription_id = Column(Unicode, ForeignKey(ChargeSubscription.id),
                             nullable=False)
    coupon_id = Column(Unicode, ForeignKey('coupons.id'))
    start_dt = Column(DateTime, nullable=False)
    end_dt = Column(DateTime, nullable=False)
    original_end_dt = Column(DateTime)
    due_dt = Column(DateTime, nullable=False)
    includes_trial = Column(Boolean)
    amount_base_cents = Column(Integer, nullable=False)
    amount_after_coupon_cents = Column(Integer, nullable=False)
    amount_paid_cents = Column(Integer, nullable=False)
    remaining_balance_cents = Column(Integer, nullable=False)
    quantity = Column(
        Integer, CheckConstraint('quantity >= 0'), nullable=False)
    prorated = Column(Boolean)
    charge_at_period_end = Column(Boolean)
    cleared_by_txn = Column(Unicode, ForeignKey('charge_transactions.id'))

    subscription = relationship('ChargeSubscription',
                                backref=backref('invoices',
                                                cascade='delete,delete-orphan', lazy='dynamic'),
                                )

    @classmethod
    def create(cls, subscription, coupon, start_dt, end_dt, due_dt,
               amount_base_cents, amount_after_coupon_cents, amount_paid_cents,
               remaining_balance_cents, quantity, charge_at_period_end,
               includes_trial=False):
        coupon_id = coupon and coupon.guid
        new_invoice = cls(
            subscription_id=subscription.id,
            coupon_id=coupon_id,
            start_dt=start_dt,
            end_dt=end_dt,
            due_dt=due_dt,
            original_end_dt=end_dt,
            amount_base_cents=amount_base_cents,
            amount_after_coupon_cents=amount_after_coupon_cents,
            amount_paid_cents=amount_paid_cents,
            remaining_balance_cents=remaining_balance_cents,
            quantity=quantity,
            charge_at_period_end=charge_at_period_end,
            includes_trial=includes_trial,
        )
        cls.session.add(new_invoice)
        return new_invoice

    @classmethod
    def prorate_last(cls, customer, plan):
        """
        Prorates the last invoice when changing a users plan. Only use when
        changing a users plan.
        """
        subscription = ChargeSubscription.query.filter(
            ChargeSubscription.customer_id == customer.id,
            ChargeSubscription.plan_id == plan.id,
            ChargeSubscription.should_renew == True).first()
        current_invoice = subscription and subscription.current_invoice
        if current_invoice:
            now = datetime.utcnow()
            true_start = current_invoice.start_dt
            if current_invoice.includes_trial and plan.trial_interval:
                true_start = true_start + plan.trial_interval
            if current_invoice:
                time_total = Decimal(
                    (current_invoice.end_dt - true_start).total_seconds())
                time_used = Decimal(
                    (now - true_start).total_seconds())
                percent_used = time_used / time_total
                new_base_amount = current_invoice.amount_base_cents * \
                    percent_used
                new_after_coupon_amount = \
                    current_invoice.amount_after_coupon_cents * percent_used
                new_balance = \
                    new_after_coupon_amount - current_invoice.amount_paid_cents
                current_invoice.amount_base_cents = new_base_amount
                current_invoice.amount_after_coupon_cents = new_after_coupon_amount
                current_invoice.remaining_balance_cents = new_balance
                current_invoice.end_dt = now
                current_invoice.subscription.should_renew = False
                current_invoice.subscription.is_enrolled = False
                current_invoice.prorated = True
        return current_invoice

    @classmethod
    def all_due(cls, customer):
        """
        Returns a list of invoices that are due for a customers
        """
        now = datetime.utcnow()
        results = ChargePlanInvoice.query.filter(
            ChargeSubscription.customer_id == customer.id,
            ChargePlanInvoice.remaining_balance_cents != 0,
            ChargePlanInvoice.due_dt <= now,
        ).all()
        return results

    def reinvoice(self):
        """
        Rollover the invoice
        """
        customer = self.subscription.customer
        plan = self.subscription.plan
        ChargeSubscription.subscribe(
            customer=customer,
            plan=plan,
            quantity=self.quantity,
            charge_at_period_end=self.charge_at_period_end,
            start_dt=self.end_dt)

    @classmethod
    def reinvoice_all(cls):
        """
        Roll
        """
        now = datetime.utcnow()
        needs_reinvoicing = cls.query.join(ChargeSubscription).filter(
            cls.end_dt <= now,
            ChargeSubscription.is_active == True,
            cls.remaining_balance_cents == 0,
        ).all()
        for plan_invoice in needs_reinvoicing:
            plan_invoice.reinvoice()
        return len(needs_reinvoicing)
