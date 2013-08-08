from __future__ import unicode_literals
from datetime import datetime

from sqlalchemy import Column, Unicode, DateTime, Integer
from sqlalchemy.schema import ForeignKey, UniqueConstraint
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import relationship

import settings
from models import (Base, PayoutSubscription, PayoutPlanInvoice, ChargeSubscription,
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

    @classmethod
    def settle_all_payouts(cls):
        now = datetime.utcnow()
        customers_need_payout = cls.query.join(PayoutSubscription).join(
            PayoutPlanInvoice).filter(PayoutPlanInvoice.payout_date <= now,
                                  PayoutPlanInvoice.completed == False).all()
        for customer in customers_need_payout:
            customer.settle_payouts()
        return True

    def settle_payout(self, force=False):
        now = datetime.utcnow()
        invoices = PayoutPlanInvoice.join(PayoutSubscription).join(Customer).query(
            Customer.id == self.id, PayoutPlanInvoice.payout_date <= now,
            PayoutPlanInvoice.completed == False).all()
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
