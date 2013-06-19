from datetime import datetime

from pytz import UTC
from sqlalchemy import Column, Unicode, ForeignKey, DateTime, Boolean, \
    Integer, ForeignKeyConstraint, Index
from sqlalchemy.orm import relationship, validates

from billy.models import Base, Group, Customer, Payout
from billy.settings import RETRY_DELAY_PAYOUT, TRANSACTION_PROVIDER_CLASS
from billy.utils.billy_action import ActionCatalog
from billy.utils.models import uuid_factory


class PayoutInvoice(Base):
    __tablename__ = 'payout_invoices'

    guid = Column(Unicode, primary_key=True, default=uuid_factory('POI'))
    customer_id = Column(Unicode)
    group_id = Column(Unicode, ForeignKey(Group.external_id))
    relevant_payout = Column(Unicode)
    created_at = Column(DateTime(timezone=UTC), default=datetime.now(UTC))
    payout_date = Column(DateTime(timezone=UTC))
    balance_to_keep_cents = Column(Integer)
    amount_payed_out = Column(Integer)
    completed = Column(Boolean, default=False)
    active = Column(Boolean, default=True)
    balance_at_exec = Column(Integer)
    cleared_by = Column(Unicode, ForeignKey('payout_transactions.guid'))
    attempts_made = Column(Integer, default=0)

    payout = relationship('Payout', backref='invoices',
                          foreign_keys=[relevant_payout, group_id])

    __table_args__ = (
        # Customer foreign key
        ForeignKeyConstraint(
            [customer_id, group_id],
            [Customer.external_id, Customer.group_id]),
        # Payout foreign key
        ForeignKeyConstraint(
            [relevant_payout, group_id],
            [Payout.external_id, Payout.group_id]),
        Index('unique_payout_invoice', relevant_payout, group_id, customer_id,
              postgresql_where=active == True, unique=True)

    )

    @classmethod
    def create(cls, customer_id, group_id, relevant_payout,
               payout_date, balanced_to_keep_cents):
        new_invoice = cls(
            customer_id=customer_id,
            group_id=group_id,
            relevant_payout=relevant_payout,
            payout_date=payout_date,
            balance_to_keep_cents=balanced_to_keep_cents,
        )
        new_invoice.event = ActionCatalog.POI_CREATE
        cls.session.add(new_invoice)
        cls.session.commit()
        return new_invoice

    @classmethod
    def retrieve(cls, customer_id, group_id, relevant_payout=None,
                         active_only=False, only_incomplete=False):
        query = cls.query.filter(cls.customer_id == customer_id,
                                 cls.group_id == group_id)
        if relevant_payout:
            query = query.filter(cls.relevant_payout == relevant_payout)
        if active_only:
            query = query.filter(cls.active == True)
        if only_incomplete:
            query = query.filter(cls.completed == False)
        return query.one()

    @classmethod
    def list(cls, group_id, relevant_payout=None,
                      customer_id=None, active_only=False):
        query = cls.query.filter(cls.group_id == group_id)
        if customer_id:
            query = query.filter(cls.customer_id == customer_id)
        if active_only:
            query = query.filter(cls.active == True)
        if relevant_payout:
            query = query.filter(cls.payout_id == relevant_payout)
        return query.all()

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
        self.event = ActionCatalog.POI_ROLLOVER
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
                transaction = PayoutTransaction.create(self.customer_id, self.group_id, payout_amount)
                try:
                    transaction.execute()
                    self.cleared_by = transaction.guid
                    self.balance_at_exec = current_balance
                    self.amount_payed_out = payout_amount
                    self.completed = True
                    self.event = ActionCatalog.POI_MAKE_PAYOUT
                except Exception, e:
                    self.event = ActionCatalog.POI_PAYOUT_ATTEMPT
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