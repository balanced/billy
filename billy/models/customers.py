from __future__ import unicode_literals
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Column, Unicode, DateTime, Integer
from sqlalchemy.schema import ForeignKeyConstraint, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from pytz import UTC
from dateutil.relativedelta import relativedelta

from billy.settings import RETRY_DELAY_PLAN
from billy.models import *
from billy.utils.models import uuid_factory
from billy.utils.billy_action import ActionCatalog


class Customer(Base):
    __tablename__ = 'customers'

    guid = Column(Unicode, primary_key=True, default=uuid_factory('CU'))
    external_id = Column(Unicode)
    group_id = Column(Unicode, ForeignKey(Group.external_id))
    current_coupon = Column(Unicode)
    created_at = Column(DateTime(timezone=UTC), default=datetime.now(UTC))
    updated_at = Column(DateTime(timezone=UTC), default=datetime.now(UTC))
    last_debt_clear = Column(DateTime(timezone=UTC))
    charge_attempts = Column(Integer, default=0)

    plan_invoices = relationship('PlanInvoice', backref='customer')
    payout_invoices = relationship('PayoutInvoice', backref='customer')
    plan_transactions = relationship('PlanTransaction',
                                     backref='customer')
    payout_transactions = relationship('PayoutTransaction',
                                       backref='customer')

    __table_args__ = (
        ForeignKeyConstraint([current_coupon, group_id],
                             ['coupons.external_id', 'coupons.group_id']),
        UniqueConstraint(external_id, group_id, name='customerid_group_unique')
    )

    @classmethod
    def create(cls, external_id, group_id):
        """
        Creates a customer for the group_id.
        :param external_id: A unique id/uri for the customer
        :param group_id: a group/group_id id/uri the user should be placed
        in (matches balanced payments group_id)
        :return: Customer Object if success or raises error if not
        :raise AlreadyExistsError: if customer already exists
        """
        new_customer = cls(
            external_id=external_id,
            group_id=group_id
        )
        new_customer.event = ActionCatalog.CUSTOMER_CREATE
        cls.session.add(new_customer)
        cls.session.commit()
        return new_customer

    @classmethod
    def retrieve(cls, external_id, group_id):
        """
        This method retrieves a single plan.
        :param external_id: A unique id/uri for the customer
        :param group_id: a group id/uri the user should be placed
        in (matches balanced payments group_id)
        :return: Customer Object if success or raises error if not
        :raise NotFoundError:  if plan not found.
        """
        query = cls.query.filter(cls.external_id == external_id,
                                 cls.group_id == group_id)
        return query.one()

    @classmethod
    def list(cls, group_id):
        """
        Returns a list of customers currently in the database
        :param group_id: The group id/uri
        :returns: A list of Customer objects
        """
        results = cls.query.filter(
            cls.group_id == group_id).all()
        return results

    def apply_coupon(self, coupon_id):
        """
        Adds a coupon to the user.
        :param coupon_id: A retrieved coupon class
        :return: Self
        :raise: LimitReachedError if coupon max redeemed.
        """
        # Todo, dirty. Fix later.
        from billy.models import Coupon

        coupon = Coupon.retrieve(coupon_id, self.group_id,
                                 active_only=True)
        if coupon.max_redeem != -1 and coupon.count_redeemed >= \
                coupon.max_redeem:
            raise ValueError('Coupon already redeemed maximum times. See '
                             'max_redeem')
        self.current_coupon = coupon_id
        self.updated_at = datetime.now(UTC)
        self.event = ActionCatalog.CUSTOMER_APPLY_COUPON
        self.session.commit()
        return self

    def remove_coupon(self):
        """
        Removes the coupon.

        """
        if not self.current_coupon:
            return self
        self.current_coupon = None
        self.updated_at = datetime.now(UTC)
        self.event = ActionCatalog.CUSTOMER_REMOVE_COUPON
        self.session.commit()
        return self

    def update_plan(self, plan_id, quantity=1,
                    charge_at_period_end=False, start_dt=None):
        """
        Changes a customer's plan
        :param plan_id: The plan id to associate customer with
        :raise:
        """
        #Todo dirty clean this...
        from billy.models import PlanInvoice
        plan = Plan.retrieve(plan_id, self.group_id, active_only=True)
        current_coupon = self.coupon
        start_date = start_dt or datetime.now(UTC)
        due_on = datetime.now(UTC)
        if current_coupon:
            coupon_use_count = PlanInvoice.query.filter(
                PlanInvoice.relevant_coupon == current_coupon.external_id,
                PlanInvoice.group_id == current_coupon.group_id,
                PlanInvoice.customer_id == self.external_id).count()
            use_coupon = True if current_coupon.repeating == -1 or \
                coupon_use_count \
                <= current_coupon.repeating else False
        else:
            use_coupon = False
        can_trial = self.can_trial_plan(plan.external_id)
        end_date = start_date + plan.plan_interval
        if can_trial:
            end_date += plan.trial_interval
            due_on += plan.trial_interval
        if charge_at_period_end:
            due_on = end_date
        amount_base = plan.price_cents * Decimal(quantity)
        amount_after_coupon = amount_base
        coupon_id = current_coupon.coupon_id if current_coupon else None
        if use_coupon and current_coupon:
            dollars_off = current_coupon.price_off_cents
            percent_off = current_coupon.percent_off_int
            amount_after_coupon -= dollars_off  # BOTH CENTS, safe
            amount_after_coupon -= int(
                amount_after_coupon * Decimal(percent_off) / Decimal(100))
        balance = amount_after_coupon
        self.prorate_last_invoice(plan_id)
        PlanInvoice.create_invoice(
            customer_id=self.external_id,
            group_id=self.group_id,
            relevant_plan=plan_id,
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
        self.event = ActionCatalog.CUSTOMER_ADD_PLAN
        self.session.commit()
        return self

    def cancel_plan(self, plan_id, cancel_at_period_end=False):
        """
        Cancels the customers subscription. You can either do it immediately
        or at the end of the period.
         in (matches balanced payments groups)
        :param cancel_at_period_end: Whether to cancel now or wait till the
        it has to renew.
        :returns: New customer object.
        """
        if cancel_at_period_end:
            result = PlanInvoice.retrieve_invoice(self.external_id,
                                                  self.group_id,
                                                  plan_id, active_only=True)
            result.active = False
            result.event = ActionCatalog.CUSTOMER_CANCEL_PLAN
            self.session.commit()
        else:
            self.prorate_last_invoice(plan_id)
        return True

    def prorate_last_invoice(self, plan_id):
        """
        Prorates the last invoice when changing a users plan. Only use when
        changing a users plan.
        in (matches balanced payments groups)
        """
        from billy.models import PlanInvoice
        right_now = datetime.now(UTC)
        last_invoice = PlanInvoice.retrieve_invoice(self.external_id,
                                                    self.group_id,
                                                    plan_id, active_only=True)
        if last_invoice:
            import ipdb;ipdb.set_trace()
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
                new_coupon_amount = last_invoice.amount_after_coupon_cents * \
                    percent_used
                new_balance = last_invoice.amount_after_coupon_cents - \
                    last_invoice.amount_paid_cents
                last_invoice.amount_base_cents = new_base_amount
                last_invoice.amount_after_coupon_cents = new_coupon_amount
                last_invoice.remaining_balance_cents = new_balance
                last_invoice.end_dt = right_now - relativedelta(
                    seconds=30)  # Extra safety for find query
                last_invoice.active = False
                last_invoice.event = ActionCatalog.PI_PRORATE_LAST
            self.session.commit()

    def add_payout(self, payout_id, first_now=False, start_dt=None):
        payout_obj = Payout.retrieve_payout(payout_id, self.group_id,
                                            active_only=True)
        first_charge = start_dt or datetime.now(UTC)
        balance_to_keep_cents = payout_obj.balance_to_keep_cents
        if not first_now:
            first_charge += payout_obj.payout_interval
        invoice = PayoutInvoice.create_invoice(self.external_id, self.group_id,
                                               payout_obj.payout_id,
                                               first_charge,
                                               balance_to_keep_cents,
                                               )
        invoice.event = ActionCatalog.CUSTOMER_ADD_PAYOUT
        self.session.add(invoice)
        self.session.commit()
        return self

    def cancel_payout(self, payout_id, cancel_scheduled=False):
        current_payout_invoice = PayoutInvoice.retrieve_invoice(
            self.external_id,
            self.group_id,
            payout_id,
            active_only=True)
        current_payout_invoice.active = False
        if cancel_scheduled:
            current_payout_invoice.completed = True
            current_payout_invoice.event = ActionCatalog.CUSTOMER_CANCEL_PAYOUT
        self.session.commit()
        return self

    @property
    def active_plans(self):
        """
        Returns a list of invoice objects pertaining to active user
        subscriptions
        """
        now = datetime.now(UTC)
        already_in = set([])
        active_list = []
        results = PlanInvoice.list_invoices(self.group_id,
                                            relevant_plan=None,
                                            customer_id=self.external_id,
                                            active_only=True).all() + \
            PlanInvoice.query.filter(PlanInvoice.group_id == self
                                     .group_id, PlanInvoice.customer_id == self.external_id,
                                     PlanInvoice.group_id == self
                                     .group_id,
                                     PlanInvoice.end_dt > now).all()
        for invoice in results:
            if invoice.guid not in already_in:
                already_in.add(invoice.guid)
                active_list.append(invoice)
        return active_list

    def can_trial_plan(self, plan_id):
        """
        Returns true/false if user has used the trial of the plan before
        :param plan_id: the external_id of the plan
        :return: True/False
        """
        #Todo fix
        from billy.models import PlanInvoice
        results = PlanInvoice.list_invoices(self.group_id,
                                            relevant_plan=plan_id,
                                            customer_id=self.external_id)
        can = True
        for each in results:
            if each.includes_trial:
                can = False
        return can

    @property
    def plan_invoices_due(self):
        now = datetime.now(UTC)
        results = PlanInvoice.filter(
            PlanInvoice.customer_id == self.external_id,
            PlanInvoice.group_id == self.group_id,
            PlanInvoice.remaining_balance_cents > 0,
            PlanInvoice.due_dt > now,
        ).all()
        return results

    def sum_plan_debt(self, plan_invoices_due):
        total_overdue = 0
        for invoice in plan_invoices_due:
            rem_bal = invoice.remaining_balance_cents
            total_overdue += rem_bal if rem_bal else 0
        return total_overdue

    @property
    def current_debt(self):
        """
        Returns the total outstanding debt for the customer
        """
        return self.sum_plan_debt(self.plan_invoices_due)

    def is_debtor(self, limit_cents):
        """
        Tells whether a customer is a debtor based on the provided limit
        :param limit_cents: Amount in cents which marks a user as a debtor. i
        .e if total_debt > limit_cents they are a debtor. Can be 0.
        :return:
        """
        total_overdue = self.current_debt
        if total_overdue > limit_cents:
            return True
        else:
            return False

    def clear_plan_debt(self, force=False):
        now = datetime.now(UTC)
        earliest_due = datetime.now(UTC)
        plan_invoices_due = self.plan_invoices_due
        for plan_invoice in plan_invoices_due:
            earliest_due = plan_invoice.due_dt if plan_invoice.due_dt < \
                earliest_due else earliest_due
        if len(RETRY_DELAY_PLAN) > self.charge_attempts and not force:
            for plan_invoice in plan_invoices_due:
                plan_invoice.active = False
        else:
            retry_delay = sum(RETRY_DELAY_PLAN[:self.charge_attempts])
            when_to_charge = earliest_due + retry_delay if retry_delay else \
                earliest_due
            if when_to_charge < now:
                sum_debt = self.sum_plan_debt(plan_invoices_due)
                transaction = PlanTransaction.create(self.external_id,
                                                     self.group_id, sum_debt)
                try:
                    transaction.execute()
                    for each in plan_invoices_due:
                        each.cleared_by = transaction.guid
                        each.remaining_balance_cents = 0
                    self.last_debt_clear = now
                    self.event = ActionCatalog.CUSTOMER_CLEAR_DEBT
                # Todo wtf man... really?
                except:
                    self.event = ActionCatalog.CUSTOMER_CHARGE_ATTEMPT
                    self.charge_attempts += 1
        self.session.commit()
        return self
