from __future__ import unicode_literals
from datetime import datetime
from decimal import Decimal

from pytz import UTC
from sqlalchemy import (Column, Unicode, ForeignKey, DateTime, Boolean,
                                    Integer, Index, or_)
from sqlalchemy.orm import relationship, validates

from billy.models import Base, Group, Customer, Plan, Coupon
from billy.utils.generic import uuid_factory


class PlanSubscription(Base):
    __tablename__ = 'plan_subscription'

    guid = Column(Unicode, primary_key=True, default=uuid_factory('PLL'))
    customer_id = Column(Unicode, ForeignKey(Customer.guid))
    plan_id = Column(Unicode, ForeignKey(Plan.guid))
    created_at = Column(DateTime(timezone=UTC), default=datetime.now(UTC))
    is_enrolled = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)

    __table_args__ = (
        Index('unique_plan_sub', plan_id, customer_id,
              postgresql_where=is_active == True,
              unique=True)
    )

    @classmethod
    def create_or_activate(cls, customer, plan):
        result = cls.query.filter(
            cls.customer_id == customer.guid,
            cls.plan_id == plan.guid).first()
        result = result or cls(customer_id=customer.guid, plan_id=plan.guid)
        result.is_active = True
        result.enrolled = True
        cls.session.commit()
        return result


    @classmethod
    def subscribe(cls, customer, plan, quantity=1,
                  charge_at_period_end=False, start_dt=None):
        from billy.models import PlanInvoice
        current_coupon = customer.coupon
        start_date = start_dt or datetime.now(UTC)
        due_on = start_date
        can_trial = customer.can_trial_plan(plan.external_id)
        end_date = start_date + plan.plan_interval
        if can_trial:
            end_date += plan.trial_interval
            due_on += plan.trial_interval
        if charge_at_period_end:
            due_on = end_date
        amount_base = plan.price_cents * Decimal(quantity)
        amount_after_coupon = amount_base
        coupon_id = current_coupon.external_id if current_coupon else None
        if customer.user_coupon and current_coupon:
            dollars_off = current_coupon.price_off_cents
            percent_off = current_coupon.percent_off_int
            amount_after_coupon -= dollars_off  # BOTH CENTS, safe
            amount_after_coupon -= int(
                amount_after_coupon * Decimal(percent_off) / Decimal(100))
        balance = amount_after_coupon
        new_sub = cls.create_or_activate(customer, plan)
        PlanInvoice.prorate_last(customer, plan)
        pi = PlanInvoice.create(
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
        cls.session.commit()
        return pi

    @classmethod
    def unsubscribe(cls, customer, plan, cancel_at_period_end=False):
        from billy.models import PlanInvoice

        if cancel_at_period_end:
            result = cls.query(cls.customer_id == customer.guid,
                               cls.plan_id == plan.guid,
                               cls.is_active == True).one()
            result.active = False
            cls.session.commit()
        else:
            PlanInvoice.prorate_last(customer, plan)
        return True


class PlanInvoice(Base):
    __tablename__ = 'plan_invoices'

    guid = Column(Unicode, primary_key=True, default=uuid_factory('PLI'))
    subscription_id = Column(Unicode, ForeignKey(PlanSubscription.guid))
    relevant_coupon = Column(Unicode, ForeignKey(Coupon.guid))
    created_at = Column(DateTime(timezone=UTC), default=datetime.now(UTC))
    end_dt = Column(DateTime(timezone=UTC))
    actual_end_dt = Column(DateTime(timezone=UTC))
    due_dt = Column(DateTime(timezone=UTC))
    includes_trial = Column(Boolean)
    amount_base_cents = Column(Integer)
    amount_after_coupon_cents = Column(Integer)
    amount_paid_cents = Column(Integer)
    remaining_balance_cents = Column(Integer)
    quantity = Column(Integer)
    prorated = Column(Boolean)
    charge_at_period_end = Column(Boolean)
    cleared_by_txn = Column(Unicode, ForeignKey('plan_transactions.guid'))

    subscription = relationship('PlanSubscription', backref='invoices')

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
    def prorate_last(cls, customer, plan):
        """
        Prorates the last invoice when changing a users plan. Only use when
        changing a users plan.
        in (matches balanced payments groups)
        """
        from billy.models import PlanInvoice

        right_now = datetime.now(UTC)
        last_invoice = customer.plan_invoices.filter(
            cls.end_dt >= datetime.utcnow())
        if last_invoice:
            plan = last_invoice.plan
            true_start = last_invoice.start_dt
            if last_invoice.includes_trial:
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
                last_invoice.subscription.active = False
                last_invoice.subscription.enrolled = False
                last_invoice.prorated = True
            cls.session.commit()

    @classmethod
    def due(cls, customer):
        """
        Returns a list of invoices that are due for a customer
        """
        from billy.models import PlanInvoice
        now = datetime.now(UTC)
        results = PlanInvoice.query.filter(
            PlanInvoice.customer_id == customer.guid,
            PlanInvoice.remaining_balance_cents != 0,
            PlanInvoice.due_dt <= now,
        ).all()
        return results

    @classmethod
    def needs_plan_debt_cleared(cls):
        """
        Returns a list of customer objects that need to clear their plan debt
        """
        now = datetime.now(UTC)
        results = cls.query.filter(
            cls.remaining_balance_cents > 0,
            cls.due_dt <= now).all()
        # Todo this set comprehension needs a test to avoid customer dupes
        return set([each.subscription.customer for each in results])

    @classmethod
    def need_rollover(cls):
        """
        Returns a list of PlanInvoice objects that need a rollover
        """
        now = datetime.now(UTC)
        invoices_rollover = cls.query.filter(cls.end_dt <= now,
                                             cls.active == True,
                                             cls.remaining_balance_cents == 0,
                                            ).all()
        return invoices_rollover

    def rollover(self):
        """
        Rollover the invoice
        """
        customer = self.subscription.customer
        plan = self.subscription
        PlanSubscription.subscribe(
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

    @classmethod
    def clear_all_plan_debt(cls):
        for customer in cls.needs_plan_debt_cleared():
            customer.clear_plan_debt()

    @validates('amount_base_cents')
    def validate_amount_base_cents(self, key, value):
        if not value >= 0:
            raise ValueError('{} must be greater than 0'.format(key))
        else:
            return value

    @validates('amount_after_coupon_cents')
    def validate_amount_after_coupon_cents(self, key, value):
        if not value >= 0:
            raise ValueError('{} must be greater than 0'.format(key))
        else:
            return value

    @validates('amount_paid_cents')
    def validate_amount_paid_cents(self, key, value):
        if not value >= 0:
            raise ValueError('{} must be greater than 0'.format(key))
        else:
            return value

    @validates('quantity')
    def validate_quantity(self, key, value):
        if not value > 0:
            raise ValueError('{} must be greater than 0'.format(key))
        else:
            return value
