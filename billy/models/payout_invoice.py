from datetime import datetime

from pytz import UTC
from sqlalchemy import Column, Unicode, ForeignKey, DateTime, Boolean, \
    Integer, ForeignKeyConstraint, Index
from sqlalchemy.orm import relationship, validates, backref

from billy.models import Base, Group, Customer, Payout
from billy.settings import RETRY_DELAY_PAYOUT, TRANSACTION_PROVIDER_CLASS
from billy.utils.generic import uuid_factory


class PayoutSubscription(Base):
    __tablename__ = 'payout_subscription'

    guid = Column(Unicode, primary_key=True, default=uuid_factory('PLL'))
    customer_id = Column(Unicode, ForeignKey(Customer.guid))
    payout_id = Column(Unicode, ForeignKey(Payout.guid))
    created_at = Column(DateTime(timezone=UTC), default=datetime.now(UTC))
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
        result = result or cls(customer_id=customer.guid, payout_id=payout.guid,
                           # Todo Temp since default not working for some reason
                               guid=uuid_factory('PLL')())
        result.is_active = True
        cls.session.add(result)
        # Todo premature commit might cause issues....
        cls.session.commit()
        return result

    @classmethod
    def subscribe(cls, customer, payout, first_now=False, start_dt=None):
        from billy.models import PayoutInvoice

        first_charge = start_dt or datetime.now(UTC)
        balance_to_keep_cents = payout.balance_to_keep_cents
        if not first_now:
            first_charge += payout.payout_interval
        new_sub = cls.create_or_activate(customer, payout)
        invoice = PayoutInvoice.create(new_sub.guid,
                                       first_charge,
                                       balance_to_keep_cents,
        )
        cls.session.add(invoice)
        cls.session.commit()
        return new_sub

    @classmethod
    def unsubscribe(cls, customer, payout, cancel_scheduled=False):
        from billy.models import PayoutInvoice

        current_sub = cls.query.filter(cls.customer_id == customer.guid,
                                       cls.payout_id == payout.guid,
                                       cls.is_active == True
        ).one()
        current_sub.is_active = False
        if cancel_scheduled:
            in_process = current_sub.invoices.filter(
                PayoutInvoice.completed == False).one()
            in_process.completed = True
        cls.session.commit()
        return True


class PayoutInvoice(Base):
    __tablename__ = 'payout_invoices'

    guid = Column(Unicode, primary_key=True, default=uuid_factory('POI'))
    subscription_id = Column(Unicode, ForeignKey(PayoutSubscription.guid))
    created_at = Column(DateTime(timezone=UTC), default=datetime.now(UTC))
    payout_date = Column(DateTime(timezone=UTC))
    balance_to_keep_cents = Column(Integer)
    amount_payed_out = Column(Integer)
    completed = Column(Boolean, default=False)
    balance_at_exec = Column(Integer)
    cleared_by_txn = Column(Unicode, ForeignKey('payout_transactions.guid'))
    attempts_made = Column(Integer, default=0)

    subscription = relationship('PayoutSubscription',
                                backref=backref('invoices',lazy='dynamic'))

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
    def needs_payout_made(cls):
        now = datetime.now(UTC)
        return cls.query.filter(cls.payout_date <= now,
                                cls.completed == False
        ).all()

    @classmethod
    def needs_rollover(cls):
        # Todo: create a better query for this...
        results = cls.query.filter(cls.completed == True).all()
        return results.subscriptions.filter(
            PayoutSubscription.is_active == True).all()

    def rollover(self):
        self.subscription.is_active = False
        self.session.flush()
        PayoutSubscription.subscribe(self.subscription.customer,
                                     self.subscription.plan,
                                     first_now=False,
                                     start_dt=self.payout_date)

    def make_payout(self, force=False):
        from billy.models import PayoutTransaction

        now = datetime.now(UTC)
        current_balance = TRANSACTION_PROVIDER_CLASS.check_balance(
            self.subscription.customer.guid, self.subscription.customer.group_id)
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
                    self.customer_id, payout_amount)
                try:
                    transaction.execute()
                    self.cleared_by = transaction.guid
                    self.balance_at_exec = current_balance
                    self.amount_payed_out = payout_amount
                    self.completed = True
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

    @validates('balance_to_keep_cents')
    def validate_balance_to_keep_cents(self, key, value):
        if not value >= 0:
            raise ValueError('{} must be >= to 0'.format(key))
        else:
            return value

    @validates('amount_payed_out')
    def validate_amount_payed_out(self, key, value):
        if not value >= 0:
            raise ValueError('{} must be >= to 0'.format(key))
        else:
            return value

    @validates('balance_at_exec')
    def validate_balance_at_exec(self, key, value):
        if not value >= 0:
            raise ValueError('{} must be >= to 0'.format(key))
        else:
            return value

    @validates('attempts_made')
    def validate_attempts_made(self, key, value):
        if not value >= 0:
            raise ValueError('{} must be >= to 0'.format(key))
        else:
            return value
