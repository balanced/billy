from __future__ import unicode_literals
from datetime import datetime

from sqlalchemy import Column, Unicode, DateTime, Integer, or_
from sqlalchemy.schema import ForeignKey, UniqueConstraint
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import relationship

from settings import RETRY_DELAY_PLAN
from models import *
from utils.generic import uuid_factory


class Customer(Base):
    __tablename__ = 'customers'

    guid = Column(Unicode, primary_key=True, default=uuid_factory('CU'))
    company_id = Column(Unicode, ForeignKey(Company.guid), nullable=False)
    external_id = Column(Unicode, nullable=False)
    processor_id = Column(Unicode, nullable=False)
    current_coupon = Column(Unicode, ForeignKey(Coupon.guid))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    last_debt_clear = Column(DateTime)
    # Todo this should be normalized and made a property:
    charge_attempts = Column(Integer, default=0)

    charge_subscriptions = relationship('ChargeSubscription',
                                        backref='customer',
                                        cascade='delete', lazy='dynamic')
    payout_subscriptions = relationship('PayoutSubscription',
                                        backref='customer',
                                        cascade='delete', lazy='dynamic')
    charge_invoices = association_proxy('charge_subscriptions', 'invoices')
    payout_invoices = association_proxy('payout_subscriptions', 'invoices')

    charge_transactions = relationship('ChargeTransaction',
                                       backref='customer', cascade='delete',
                                       lazy='dynamic'
                                       )
    payout_transactions = relationship('PayoutTransaction',
                                       backref='customer', cascade='delete',
                                       lazy='dynamic')

    __table_args__ = (
        UniqueConstraint(
            external_id, company_id, name='customerid_company_unique'),
    )

    def update(self, processor_id):
        if not self.company.processor_class.can_add_customer(processor_id):
            raise ValueError('processor_id')
        self.processor_id = processor_id
        try:
            self.session.commit()
        except:
            self.session.rollback()
            raise
        return self

    def remove_coupon(self):
        """
        Removes the coupon.

        """
        if not self.current_coupon:
            return self
        self.current_coupon = None
        self.updated_at = datetime.utcnow()
        self.session.commit()
        return self

    @property
    def coupon_use_count(self):
        """
        The number of times the current coupon has been used
        """
        count = 0 if not self.current_coupon else self.plan_invoices.filter(
            ChargePlanInvoice.relevant_coupon == self.current_coupon).count()
        return count

    @property
    def can_use_current_coupon(self):
        """
        Whether or not a coupon can be applied to an invoice this is for
        scenarios where
        """
        use_coupon = self.current_coupon or True \
            if self.current_coupon.repeating == -1 or \
            self.coupon_use_count <= self.current_coupon.repeating else False
        return use_coupon

    @property
    def total_charge_debt(self):
        """
        Returns the total outstanding debt for the customer
        """
        total_overdue = 0
        for invoice in ChargePlanInvoice.all_due(self):
            rem_bal = invoice.remaining_balance_cents
            total_overdue += rem_bal if rem_bal else 0
        return total_overdue

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

    @classmethod
    def needs_charge_debt_cleared(cls):
        """
        Returns a list of customer objects that need to clear their plan debt
        """
        from models import ChargePlanInvoice

        now = datetime.utcnow()
        return cls.query.join(ChargeSubscription).join(
            ChargePlanInvoice).filter(
                ChargePlanInvoice.remaining_balance_cents > 0,
                ChargePlanInvoice.due_dt <= now
            ).all()

    @classmethod
    def clear_charge_debt(cls):
        for customer in cls.needs_plan_debt_cleared():
            customer.clear_charge_debt()

    def clear_charge_debt(self, force=False):
        """
        Clears the charge debt of the customer.
        """
        from models import ChargePlanInvoice, ChargeTransaction

        now = datetime.utcnow()
        earliest_due = datetime.utcnow()
        plan_invoices_due = ChargePlanInvoice.all_due(self)
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
                transaction = ChargeTransaction.create(self.guid, sum_debt)
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
