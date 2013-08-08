from __future__ import unicode_literals
from datetime import datetime

from sqlalchemy import Column, Unicode, DateTime, Integer
from sqlalchemy.schema import ForeignKey, UniqueConstraint
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import relationship

import settings
from models import (Base, PayoutSubscription, PayoutInvoice, ChargeSubscription,
                    ChargePlanInvoice, ChargeTransaction, PayoutTransaction)
from utils.models import uuid_factory


class Customer(Base):
    __tablename__ = 'customers'

    id = Column(Unicode, primary_key=True, default=uuid_factory('CU'))
    company_id = Column(Unicode, ForeignKey('companies.id'), nullable=False)
    your_id = Column(Unicode, nullable=False)
    processor_id = Column(Unicode, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow)
    last_debt_clear = Column(DateTime)
    # Todo this should be normalized and made a property:
    charge_attempts = Column(Integer, default=0)

    # Charge Relationships
    charge_subscriptions = relationship('ChargeSubscription',
                                        backref='customer',
                                        cascade='delete', lazy='dynamic')
    charge_invoices = association_proxy('charge_subscriptions', 'invoices')

    charge_transactions = relationship('ChargeTransaction',
                                       backref='customer', cascade='delete',
                                       lazy='dynamic'
    )

    # Payout Relationships
    payout_subscriptions = relationship('PayoutSubscription',
                                        backref='customer',
                                        cascade='delete', lazy='dynamic')
    payout_invoices = association_proxy('payout_subscriptions', 'invoices')

    payout_transactions = relationship('PayoutTransaction',
                                       backref='customer', cascade='delete',
                                       lazy='dynamic')

    __table_args__ = (
        UniqueConstraint(
            your_id, company_id, name='customerid_company_unique'),
    )


    @property
    def total_charge_debt(self, invoices=None):
        """
        Returns the total outstanding debt for the customer
        """
        total_overdue = 0
        if not invoices:
            invoices = ChargePlanInvoice.all_due(self)
        for invoice in invoices:
            rem_bal = invoice.remaining_balance_cents
            total_overdue += rem_bal if rem_bal else 0
        return total_overdue

    @classmethod
    def needs_charge_debt_settled(cls):
        """
        Returns a list of customer objects that need to clear their plan debt
        """
        now = datetime.utcnow()
        return cls.query.join(ChargeSubscription).join(
            ChargePlanInvoice).filter(
            ChargePlanInvoice.remaining_balance_cents > 0,
            ChargePlanInvoice.due_dt <= now).all()

    @classmethod
    def settle_all_charge_plan_debt(cls):
        for customer in cls.needs_charge_debt_settled():
            customer.settle_charge_plan_debt()

    def settle_charge_plan_debt(self, force=False):
        """
        Clears the charge debt of the customer.
        """
        now = datetime.utcnow()
        earliest_due = datetime.utcnow()
        plan_invoices_due = ChargePlanInvoice.all_due(self)
        for plan_invoice in plan_invoices_due:
            earliest_due = plan_invoice.due_dt if plan_invoice.due_dt < \
                                                  earliest_due else earliest_due
            # Cancel a users plan if max retries reached
        if len(settings.RETRY_DELAY_PLAN) < self.charge_attempts and not force:
            for plan_invoice in plan_invoices_due:
                plan_invoice.subscription.is_active = False
                plan_invoice.subscription.is_enrolled = False
        else:
            retry_delay = sum(settings.RETRY_DELAY_PLAN[:self.charge_attempts])
            when_to_charge = earliest_due + retry_delay if retry_delay else \
                earliest_due
            if when_to_charge <= now:
                sum_debt = self.total_charge_debt(plan_invoices_due)
                transaction = ChargeTransaction.create(self.id, sum_debt)
                try:
                    transaction.execute()
                    for each in plan_invoices_due:
                        each.cleared_by = transaction.id
                        each.remaining_balance_cents = 0
                    self.last_debt_clear = now
                except Exception, e:
                    self.charge_attempts += 1
                    self.session.commit()
                    raise e
        return self

    @classmethod
    def settle_all_payouts(cls):
        now = datetime.utcnow()
        customers_need_payout = cls.query.join(PayoutSubscription).join(
            PayoutInvoice).filter(PayoutInvoice.payout_date <= now,
                                  PayoutInvoice.completed == False).all()
        for customer in customers_need_payout:
            customer.settle_payouts()
        return True

    def settle_payout(self, force=False):
        now = datetime.utcnow()
        invoices = PayoutInvoice.join(PayoutSubscription).join(Customer).query(
            Customer.id == self.id, PayoutInvoice.payout_date <= now,
            PayoutInvoice.completed == False).all()
        for invoice in invoices:
            transactor = self.company.processor
            current_balance = transactor.check_balance(
                self.processor_id,
                self.group_id)
            payout_date = invoice.payout_date
            if len(
                    settings.RETRY_DELAY_PAYOUT) < invoice.attempts_made and not force:
                invoice.subscription.is_active = False
            else:
                retry_delay = sum(
                    settings.RETRY_DELAY_PAYOUT[:invoice.attempts_made])
                when_to_payout = payout_date + retry_delay if retry_delay else \
                    payout_date
                if when_to_payout <= now:
                    payout_amount = current_balance - \
                                    invoice.balance_to_keep_cents
                    transaction = PayoutTransaction.create(
                        invoice.subscription.customer_id, payout_amount)
                    try:
                        transaction.execute()
                        invoice.cleared_by = transaction.id
                        invoice.balance_at_exec = current_balance
                        invoice.amount_payed_out = payout_amount
                        invoice.completed = True
                        invoice.queue_rollover = True
                    except Exception, e:
                        invoice.attempts_made += 1
                        invoice.session.commit()
                        raise e
            self.session.commit()
        return self
