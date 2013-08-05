from __future__ import unicode_literals
from datetime import datetime
from decimal import Decimal

from pytz import UTC
from sqlalchemy import (Column, Unicode, ForeignKey, DateTime, Boolean,
                        Integer, Index, CheckConstraint)
from sqlalchemy.orm import relationship, validates, backref

from models import Base, Customer, ChargePlan, Coupon
from utils.generic import uuid_factory


class ChargeSubscription(Base):
    __tablename__ = 'charge_subscription'

    guid = Column(Unicode, primary_key=True, default=uuid_factory('PLS'))
    customer_id = Column(Unicode, ForeignKey(Customer.guid), nullable=False)
    plan_id = Column(Unicode, ForeignKey(ChargePlan.guid), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_enrolled = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)

    __table_args__ = (
        Index('unique_charge_sub', plan_id, customer_id,
              postgresql_where=is_active == True,
              unique=True),
    )

    @classmethod
    def create_or_activate(cls, customer, plan):
        result = cls.query.filter(
            cls.customer_id == customer.guid,
            cls.plan_id == plan.guid).first()
        result = result or cls(
            customer_id=customer.guid, plan_id=plan.guid,
            # Todo TEMP since default not working for some reason
            guid=uuid_factory('PLS')())
        result.is_active = True
        result.is_enrolled = True
        # Todo premature commit might cause issues....
        cls.session.add(result)
        cls.session.commit()
        return result

    @classmethod
    def renewing_plans(cls, customer):
        """
        List of plans that are subscribed and enrolled that will renew come
        the next term
        """
        return cls.query.filter(cls.customer_id == customer.guid,
                                cls.is_active == True).all()

    @classmethod
    def enrolled_plans(cls, customer):
        """
        List of plans that are enrolled but sometimes aren't active. i.e when
        you cancel a plan at the end of the period
        """
        return cls.query.filter(cls.customer_id == customer.guid,
                                cls.is_enrolled == True).all()


class ChargePlanInvoice(Base):
    __tablename__ = 'charge_plan_invoices'

    guid = Column(Unicode, primary_key=True, default=uuid_factory('PLI'))
    subscription_id = Column(Unicode, ForeignKey(ChargeSubscription.guid),
                             nullable=False)
    coupon = Column(Unicode, ForeignKey(Coupon.guid), nullable=False)
    created_at = Column(DateTime(timezone=UTC), default=datetime.utcnow)
    start_dt = Column(DateTime(timezone=UTC), nullable=False)
    end_dt = Column(DateTime(timezone=UTC), nullable=False)
    original_end_dt = Column(DateTime(timezone=UTC))
    due_dt = Column(DateTime(timezone=UTC), nullable=False)
    includes_trial = Column(Boolean)
    amount_base_cents = Column(Integer,
                               CheckConstraint('amount_base_cents >= 0'),
                               nullable=False)
    amount_after_coupon_cents = Column(Integer, CheckConstraint(
        'amount_after_coupon_cents >= 0'),
        nullable=False)
    amount_paid_cents = Column(Integer,
                               CheckConstraint('amount_paid_cents >= 0'),
                               nullable=False)
    remaining_balance_cents = Column(Integer, nullable=False)
    quantity = Column(
        Integer, CheckConstraint('quantity >= 0'), nullable=False)
    prorated = Column(Boolean)
    charge_at_period_end = Column(Boolean)
    cleared_by_txn = Column(Unicode, ForeignKey('charge_transactions.guid'),
                            nullable=False)

    subscription = relationship('ChargeSubscription',
                                backref=backref('invoices', cascade='delete'))

    @classmethod
    def create(cls, subscription_id, relevant_coupon, start_dt, end_dt, due_dt,
               amount_base_cents, amount_after_coupon_cents, amount_paid_cents,
               remaining_balance_cents, quantity, charge_at_period_end,
               includes_trial=False):
        new_invoice = cls(
            subscription_id=subscription_id,
            relevant_coupon=relevant_coupon,
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
        # Todo clean this up
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
                last_invoice.subscription.is_active = False
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
