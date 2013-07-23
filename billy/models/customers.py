from __future__ import unicode_literals
from datetime import datetime

from pytz import UTC
from sqlalchemy import Column, Unicode, DateTime, Integer, or_
from sqlalchemy.schema import ForeignKey, UniqueConstraint
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import relationship

from billy.settings import RETRY_DELAY_PLAN
from billy.models import *
from billy.utils.generic import uuid_factory


class Customer(Base):
    __tablename__ = 'customers'

    guid = Column(Unicode, primary_key=True, default=uuid_factory('CU'))
    external_id = Column(Unicode)
    group_id = Column(Unicode, ForeignKey(Group.guid))
    current_coupon = Column(Unicode, ForeignKey(Coupon.guid))
    created_at = Column(DateTime(timezone=UTC), default=datetime.now(UTC))
    updated_at = Column(DateTime(timezone=UTC), default=datetime.now(UTC))
    last_debt_clear = Column(DateTime(timezone=UTC))
    # Todo this should be normalized and made a property:
    charge_attempts = Column(Integer, default=0)

    plan_sub = relationship('PlanSubscription', backref='customer')
    payout_sub = relationship('PayoutSubscription', backref='customer')

    plan_invoices = association_proxy('PlanSubscription', 'invoices')
    payout_invoices = association_proxy('PayoutSubscription', 'invoices')

    plan_transactions = relationship('PlanTransaction',
                                     backref='customer')
    payout_transactions = relationship('PayoutTransaction',
                                       backref='customer')


    __table_args__ = (
        UniqueConstraint(external_id, group_id, name='customerid_group_unique'),
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


    def apply_coupon(self, coupon_eid):
        """
        Adds a coupon to the user.
        :param coupon_eid: A retrieved coupon class
        :return: Self
        :raise: LimitReachedError if coupon max redeemed.
        """
        from billy.models import Coupon

        coupon = Coupon.retrieve(coupon_eid, self.group_id,
                                 active_only=True)
        if coupon.max_redeem != -1 and coupon.count_redeemed >= \
                coupon.max_redeem:
            raise ValueError('Coupon already redeemed maximum times. See '
                             'max_redeem')
        self.current_coupon = coupon.guid
        self.updated_at = datetime.now(UTC)
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
        self.session.commit()
        return self

    @property
    def coupon_use_count(self):
        from models import PlanInvoice
        count = 0 if not self.current_coupon else self.plan_invoices.filter(
            PlanInvoice.relevant_coupon == self.current_coupon).count()
        return count


    @property
    def can_use_coupon(self):
        use_coupon = self.current_coupon or True \
            if self.current_coupon.repeating == -1 or \
               self.coupon_use_count <= self.current_coupon.repeating else False
        return use_coupon

    def can_trial_plan(self, plan_id):
        from models import PlanSubscription
        count = PlanSubscription.query.filter(
            PlanSubscription.customer_id == self.guid,
            PlanSubscription.plan_id == plan_id
        ).count()
        return not bool(count)

    def sum_plan_debt(self, plan_invoices_due):
        total_overdue = 0
        for invoice in plan_invoices_due:
            rem_bal = invoice.remaining_balance_cents
            total_overdue += rem_bal if rem_bal else 0
        return total_overdue

    @property
    def plan_debt(self):
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
        total_overdue = self.plan_debt
        if total_overdue > limit_cents:
            return True
        else:
            return False

    def clear_plan_debt(self, force=False):
        from billy.models import PlanTransaction
        from billy.models import PlanInvoice

        now = datetime.now(UTC)
        earliest_due = datetime.now(UTC)
        plan_invoices_due = PlanInvoice.due(self)
        for plan_invoice in plan_invoices_due:
            earliest_due = plan_invoice.due_dt if plan_invoice.due_dt < \
                                                  earliest_due else earliest_due
            # Cancel a users plan if max retries reached
        if len(RETRY_DELAY_PLAN) < self.charge_attempts and not force:
            for plan_invoice in plan_invoices_due:
                plan_invoice.subscription.is_active = False
                plan_invoice.subscription.is_enrolled = False
        else:
            retry_delay = sum(RETRY_DELAY_PLAN[:self.charge_attempts])
            when_to_charge = earliest_due + retry_delay if retry_delay else \
                earliest_due
            if when_to_charge <= now:
                sum_debt = self.sum_plan_debt(plan_invoices_due)
                transaction = PlanTransaction.create(self.guid, sum_debt)
                try:
                    transaction.execute()
                    for each in plan_invoices_due:
                        each.cleared_by = transaction.guid
                        each.remaining_balance_cents = 0
                    self.last_debt_clear = now
                except Exception, e:
                    self.charge_attempts += 1
                    self.session.commit()
                    raise e
        self.session.commit()
        return self

    @property
    def plan_subscriptions(self):
        """
        Returns a list of invoice objects pertaining to active user
        subscriptions
        """
        from billy.models import PlanSubscription
        return self.plan_subscriptions.filter(
                        or_(PlanSubscription.is_active == True,
                                        PlanSubscription.is_enrolled == True))
