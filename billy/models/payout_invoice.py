from datetime import datetime

from pytz import UTC
from sqlalchemy import (Column, Unicode, ForeignKey, DateTime, Boolean,
                        Integer, CheckConstraint, Index)
from sqlalchemy.orm import relationship, validates, backref

from models import Base, Company, Customer, PayoutPlan
from settings import RETRY_DELAY_PAYOUT
from utils.generic import uuid_factory
from processor import processor_map


class PayoutSubscription(Base):
    __tablename__ = 'payout_subscription'

    guid = Column(Unicode, primary_key=True, default=uuid_factory('POS'))
    customer_id = Column(Unicode, ForeignKey(Customer.guid), nullable=False)
    payout_id = Column(Unicode, ForeignKey(PayoutPlan.guid), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    __table_args__ = (
        Index('unique_payout_sub', payout_id, customer_id,
              postgresql_where=is_active == True,
              unique=True),
    )

    @classmethod
    def create_or_activate(cls, customer, payout):
        result = cls.query.filter(
            cls.customer_id == customer.guid,
            cls.payout_id == payout.guid).first()
        result = result or cls(
            customer_id=customer.guid, payout_id=payout.guid,
            # Todo Temp since default not working for some reason
            guid=uuid_factory('PLL')())
        result.is_active = True
        cls.session.add(result)
        # Todo premature commit might cause issues....
        cls.session.commit()
        return result


class PayoutInvoice(Base):
    __tablename__ = 'payout_invoices'

    guid = Column(Unicode, primary_key=True, default=uuid_factory('POI'))
    subscription_id = Column(Unicode, ForeignKey(PayoutSubscription.guid),
                             nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    payout_date = Column(DateTime)
    balance_to_keep_cents = Column(Integer, CheckConstraint(
        'balance_to_keep_cents >= 0'))
    amount_payed_out = Column(Integer)
    completed = Column(Boolean, default=False)
    queue_rollover = Column(Boolean, default=False)
    balance_at_exec = Column(Integer,
                             nullable=True)
    cleared_by_txn = Column(Unicode, ForeignKey('payout_transactions.guid'))
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
        cls.session.commit()
        return new_invoice

    @classmethod
    def retrieve(cls, customer, payout, active_only=False, last_only=False):
        # Todo can probably be cleaner
        query = PayoutSubscription.query.filter(
            PayoutSubscription.customer_id == customer.guid,
            PayoutSubscription.payout_id == payout.guid)
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
    def needs_payout_made(cls):
        now = datetime.utcnow()
        return cls.query.filter(cls.payout_date <= now,
                                cls.completed == False).all()

    @classmethod
    def needs_rollover(cls):
        # Todo: create a better query for this...
        results = cls.query.join(
            PayoutSubscription).filter(cls.queue_rollover == True,
                                       PayoutSubscription.is_active == True) \
            .all()
        return results

    def rollover(self):
        self.subscription.is_active = False
        self.queue_rollover = False
        self.session.flush()
        PayoutSubscription.subscribe(self.subscription.customer,
                                     self.subscription.payout,
                                     first_now=False,
                                     start_dt=self.payout_date)

    def make_payout(self, force=False):
        from models import PayoutTransaction

        now = datetime.utcnow()
        transaction_class = processor_map[
            self.subscription.customer.group.provider](
            self.customer.group.provider_api_key)
        current_balance = transaction_class.check_balance(
            self.subscription.customer.guid,
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
                    self.cleared_by = transaction.guid
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

    @classmethod
    def make_all_payouts(cls):
        payout_invoices = cls.needs_payout_made()
        for invoice in payout_invoices:
            invoice.make_payout()
        return True

    @classmethod
    def rollover_all(cls):
        need_rollover = cls.needs_rollover()
        for payout in need_rollover:
            payout.rollover()
