from datetime import datetime

from pytz import UTC
from sqlalchemy import Column, Unicode, ForeignKey, DateTime, Boolean, \
    Integer, ForeignKeyConstraint, Index
from sqlalchemy.orm import relationship, validates

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
              unique=True)
    )

    @classmethod
    def create_or_activate(cls, customer, payout):
        result = cls.query.filter(
            cls.customer_id == customer.guid,
            cls.payout_id == payout.guid).first()
        result = result or cls(customer_id=customer.guid, payout_id=payout.guid)
        result.active = True
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
        invoice = PayoutInvoice.create(self.external_id, self.group_id,
                                       payout.external_id,
                                       first_charge,
                                       balance_to_keep_cents,
        )
        self.session.add(invoice)
        self.session.commit()
        return self

    @classmethod
    def unsubscribe(cls, customer, payout_id, cancel_scheduled=False):
        from billy.models import PayoutInvoice

        current_payout_invoice = PayoutInvoice.retrieve(
            self.external_id,
            self.group_id,
            payout_id,
            active_only=True)
        current_payout_invoice.active = False
        if cancel_scheduled:
            current_payout_invoice.completed = True
        self.session.commit()
        return self


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

    subscription = relationship('PlanSubscription', backref='invoices')

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

    # @classmethod
    # def retrieve(cls, customer_id, group_id, relevant_payout=None,
    #              active_only=False, only_incomplete=False):
    #     query = cls.query.filter(cls.customer_id == customer_id,
    #                              cls.group_id == group_id)
    #     if relevant_payout:
    #         query = query.filter(cls.relevant_payout == relevant_payout)
    #     if active_only:
    #         query = query.filter(cls.active == True)
    #     if only_incomplete:
    #         query = query.filter(cls.completed == False)
    #     return query.one()
    #
    # @classmethod
    # def list(cls, group_id, relevant_payout=None,
    #          customer_id=None, active_only=False):
    #     query = cls.query.filter(cls.group_id == group_id)
    #     if customer_id:
    #         query = query.filter(cls.customer_id == customer_id)
    #     if active_only:
    #         query = query.filter(cls.active == True)
    #     if relevant_payout:
    #         query = query.filter(cls.relevant_payout == relevant_payout)
    #     return query.all()

    @classmethod
    def needs_payout_made(cls):
        now = datetime.now(UTC)
        return cls.query.filter(cls.payout_date <= now,
                                cls.completed == False
                                ).all()

    @classmethod
    def needs_rollover(cls):
        return cls.query.filter(cls.completed == True,
                                cls.active == True).all()

    def rollover(self):
        self.active = False
        self.session.flush()
        self.customer.add_payout(self.relevant_payout, first_now=False,
                                 start_dt=self.payout_date)

    def make_payout(self, force=False):
        from billy.models import PayoutTransaction
        now = datetime.now(UTC)
        current_balance = TRANSACTION_PROVIDER_CLASS.check_balance(
            self.customer_id, self.group_id)
        payout_date = self.payout_date
        if len(RETRY_DELAY_PAYOUT) < self.attempts_made and not force:
            self.active = False
        else:
            retry_delay = sum(RETRY_DELAY_PAYOUT[:self.attempts_made])
            when_to_payout = payout_date + retry_delay if retry_delay else \
                payout_date
            if when_to_payout <= now:
                payout_amount = current_balance - self.balance_to_keep_cents
                transaction = PayoutTransaction.create(
                    self.customer_id, self.group_id, payout_amount)
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
