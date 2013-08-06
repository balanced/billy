from __future__ import unicode_literals
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (Column, Unicode, ForeignKey, DateTime, Boolean,
                        Integer, CheckConstraint)
from sqlalchemy.orm import relationship, backref

from models import Base, Coupon
from models.charge_subscription import ChargeSubscription
from utils.generic import uuid_factory


class ChargePlanInvoice(Base):
    __tablename__ = 'charge_plan_invoices'

    guid = Column(Unicode, primary_key=True, default=uuid_factory('PLI'))
    subscription_id = Column(Unicode, ForeignKey(ChargeSubscription.guid),
                             nullable=False)
    coupon_id = Column(Unicode, ForeignKey(Coupon.guid), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    start_dt = Column(DateTime, nullable=False)
    end_dt = Column(DateTime, nullable=False)
    original_end_dt = Column(DateTime)
    due_dt = Column(DateTime, nullable=False)
    includes_trial = Column(Boolean)
    amount_base_cents = Column(Integer, nullable=False)
    amount_after_coupon_cents = Column(Integer, nullable=False)
    amount_paid_cents = Column(Integer, nullable=False)
    remaining_balance_cents = Column(Integer, nullable=False)
    quantity = Column(Integer, CheckConstraint('quantity >= 0'), nullable=False)
    prorated = Column(Boolean)
    charge_at_period_end = Column(Boolean)
    cleared_by_txn = Column(Unicode, ForeignKey('charge_transactions.guid'))

    subscription = relationship('ChargeSubscription',
                                backref=backref('invoices', cascade='delete'))

    @classmethod
    def create(cls, subscription_id, relevant_coupon, start_dt, end_dt, due_dt,
               amount_base_cents, amount_after_coupon_cents, amount_paid_cents,
               remaining_balance_cents, quantity, charge_at_period_end,
               includes_trial=False):
        new_invoice = cls(
            subscription_id=subscription_id,
            coupon=relevant_coupon,
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
        cls.session.commit()
        return new_invoice

    @classmethod
    def retrieve(cls, customer, plan, active_only=False, last_only=False):
        # Todo clean this up, or reconsider model
        query = ChargeSubscription.query.filter(
            ChargeSubscription.customer_id == customer.guid,
            ChargeSubscription.plan_id == plan.guid)
        if active_only:
            query = query.filter(ChargeSubscription.is_active == True)
        subscription = query.first()
        if subscription and last_only:
            last = None
            for invoice in subscription.invoices:
                if invoice.end_dt >= datetime.utcnow():
                    last = invoice
                    break
            return last
        return subscription.invoices

    @classmethod
    def prorate_last(cls, customer, plan):
        """
        Prorates the last invoice when changing a users plan. Only use when
        changing a users plan.
        """
        right_now = datetime.utcnow()
        last_invoice = cls.retrieve(customer, plan, True, True)
        if last_invoice:
            true_start = last_invoice.start_dt
            if last_invoice.includes_trial and plan.trial_interval:
                true_start = true_start + plan.trial_interval
            if last_invoice:
                time_total = Decimal(
                    (last_invoice.end_dt - true_start).total_seconds())
                time_used = Decimal(
                    (right_now - true_start).total_seconds())
                percent_used = time_used / time_total
                new_base_amount = last_invoice.amount_base_cents * percent_used
                new_after_coupon_amount = \
                    last_invoice.amount_after_coupon_cents * percent_used
                new_balance = \
                    new_after_coupon_amount - last_invoice.amount_paid_cents
                last_invoice.amount_base_cents = new_base_amount
                last_invoice.amount_after_coupon_cents = new_after_coupon_amount
                last_invoice.remaining_balance_cents = new_balance
                last_invoice.end_dt = right_now
                last_invoice.subscription.should_renew = False
                last_invoice.subscription.is_enrolled = False
                last_invoice.prorated = True
            cls.session.commit()
        return last_invoice

    @classmethod
    def all_due(cls, customer):
        """
        Returns a list of invoices that are due for a customer
        """
        from models import ChargePlanInvoice

        now = datetime.utcnow()
        results = ChargePlanInvoice.query.filter(
            ChargeSubscription.customer_id == customer.guid,
            ChargePlanInvoice.remaining_balance_cents != 0,
            ChargePlanInvoice.due_dt <= now,
        ).all()
        return results

    @classmethod
    def need_rollover(cls):
        """
        Returns a list of ChargePlanInvoice objects that need a rollover
        """
        now = datetime.utcnow()
        invoices_rollover = cls.query.join(ChargeSubscription).filter(
            cls.end_dt <= now,
            ChargeSubscription.is_active == True,
            cls.remaining_balance_cents == 0,
        ).all()
        return invoices_rollover

    def rollover(self):
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
        self.session.commit()

    @classmethod
    def rollover_all(cls):
        to_rollover = cls.need_rollover()
        for plan_invoice in to_rollover:
            plan_invoice.rollover()
        return len(to_rollover)
