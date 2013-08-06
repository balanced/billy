from datetime import datetime

from sqlalchemy import (Column, Unicode, ForeignKey, DateTime, Boolean,
                        Integer, CheckConstraint)
from sqlalchemy.orm import relationship, backref

from models import Base, PayoutSubscription
from settings import RETRY_DELAY_PAYOUT
from utils.generic import uuid_factory
from processor import processor_map


class PayoutInvoice(Base):
    __tablename__ = 'payout_invoices'

    id = Column(Unicode, primary_key=True, default=uuid_factory('POI'))
    subscription_id = Column(Unicode, ForeignKey(PayoutSubscription.id),
                             nullable=False)
    payout_date = Column(DateTime)
    balance_to_keep_cents = Column(Integer, CheckConstraint(
        'balance_to_keep_cents >= 0'))
    amount_payed_out = Column(Integer)
    completed = Column(Boolean, default=False)
    queue_rollover = Column(Boolean, default=False)
    balance_at_exec = Column(Integer,
                             nullable=True)
    cleared_by_txn = Column(Unicode, ForeignKey('payout_transactions.id'))
    attempts_made = Column(Integer, CheckConstraint('attempts_made >= 0'),
                           default=0)

    subscription = relationship('PayoutSubscription',
                                backref=backref('invoices', lazy='dynamic',
                                                cascade='delete'),
                                )

    @classmethod
    def create(cls, subscription_id,
               payout_date, balanced_to_keep_cents):
        new_invoice = cls(
            subscription_id=subscription_id,
            payout_date=payout_date,
            balance_to_keep_cents=balanced_to_keep_cents,
        )
        cls.session.add(new_invoice)
        return new_invoice

    @classmethod
    def retrieve(cls, customer, payout, active_only=False, last_only=False):
        # Todo can probably be cleaner
        query = PayoutSubscription.query.filter(
            PayoutSubscription.customer_id == customer.id,
            PayoutSubscription.payout_id == payout.id)
        if active_only:
            query = query.filter(PayoutSubscription.is_active == True)
        subscription = query.first()
        if subscription and last_only:
            last = None
            for invoice in subscription.invoices:
                if invoice.payout_date >= datetime.utcnow():
                    last = invoice
                    break
            return last
        return subscription.invoices

    @classmethod
    def rollover_all(cls):
        need_rollover = cls.query.join(PayoutSubscription).filter(
            cls.queue_rollover == True,
            PayoutSubscription.is_active == True).all()
        for invoice in need_rollover:
            invoice.rollover()

    def rollover(self):
        self.subscription.is_active = False
        self.queue_rollover = False
        PayoutSubscription.subscribe(self.subscription.customer,
                                     self.subscription.payout,
                                     first_now=False,
                                     start_dt=self.payout_date)

    @classmethod
    def make_all_payouts(cls):
        now = datetime.utcnow()
        need_payout = cls.query.filter(cls.payout_date <= now,
                                       cls.completed == False).all()
        for invoice in need_payout:
            invoice.make_payout()
        return True

    def make_payout(self, force=False):
        from models import PayoutTransaction

        now = datetime.utcnow()
        transactor = self.subscription.customer.company.processor
        current_balance = transactor.check_balance(
            self.subscription.customer.id,
            self.subscription.customer.group_id)
        payout_date = self.payout_date
        if len(RETRY_DELAY_PAYOUT) < self.attempts_made and not force:
            self.subscription.is_active = False
        else:
            retry_delay = sum(RETRY_DELAY_PAYOUT[:self.attempts_made])
            when_to_payout = payout_date + retry_delay if retry_delay else \
                payout_date
            if when_to_payout <= now:
                payout_amount = current_balance - self.balance_to_keep_cents
                transaction = PayoutTransaction.create(
                    self.subscription.customer_id, payout_amount)
                try:
                    transaction.execute()
                    self.cleared_by = transaction.id
                    self.balance_at_exec = current_balance
                    self.amount_payed_out = payout_amount
                    self.completed = True
                    self.queue_rollover = True
                except Exception, e:
                    self.attempts_made += 1
                    self.session.commit()
                    raise e
        self.session.commit()
        return self
