from __future__ import unicode_literals

from pytz import UTC
from sqlalchemy import Column, Unicode, ForeignKey, DateTime, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.schema import ForeignKeyConstraint

from billy.models import Base, Customer, PlanInvoice, PayoutInvoice
from billy.utils.models import uuid_factory, Status
from billy.utils.billy_action import ActionCatalog
from billy.settings import TRANSACTION_PROVIDER_CLASS


class TransactionMixin(object):
    external_id = Column(Unicode)
    created_at = Column(DateTime(timezone=UTC))
    amount_cents = Column(Integer)
    status = Column(Unicode)

    @classmethod
    def create(cls, customer_id, group_id, amount_cents):
        new_transaction = cls(
            group_id=group_id,
            customer_id=customer_id,
            amount_cents=amount_cents,
            status=Status.PENDING
        )
        new_transaction.event = ActionCatalog.TR_CREATE
        cls.session.add(new_transaction)
        cls.session.commit()
        return new_transaction

    @classmethod
    def retrieve(cls, group_id, customer_id=None, external_id=None):
        query = cls.query.filter(cls.group_id == group_id)
        if customer_id:
            query.filter(cls.customer_id == customer_id)
        if external_id:
            query.filter(cls.external_id == external_id)
        return query.all()


class PlanTransaction(TransactionMixin, Base):
    __tablename__ = "plan_transactions"

    guid = Column(Unicode, primary_key=True, default=uuid_factory('PAT'))
    group_id = Column(Unicode, ForeignKey('groups.external_id'))
    customer_id = Column(Unicode)
    plan_invoices = relationship(PlanInvoice.__name__, backref='transaction')

    def execute(self):
        try:
            external_id = TRANSACTION_PROVIDER_CLASS.create_charge(
                self.customer_id, self.group_id,
                self.amount_cents)
            self.status = Status.COMPLETE
            self.external_id = external_id
            self.event = ActionCatalog.TR_EXECUTE_PAYMENT
        except Exception, e:
            self.status = Status.ERROR
            self.event = ActionCatalog.TR_PAYMENT_ERROR
            self.session.commit()
            raise e
        self.customer.charge_attempts = 0
        self.session.commit()

    __table_args__ = (
        # Customer foreign key
        ForeignKeyConstraint(
            [customer_id, group_id],
            [Customer.external_id, Customer.group_id]),
    )


class PayoutTransaction(TransactionMixin, Base):
    __tablename__ = 'payout_transactions'

    charge_callable = TRANSACTION_PROVIDER_CLASS.create_charge

    guid = Column(Unicode, primary_key=True, default=uuid_factory('POT'))
    payout_invoices = relationship(PayoutInvoice.__name__,
                                   backref='transaction')
    group_id = Column(Unicode)
    customer_id = Column(Unicode)

    def execute(self):
        try:
            external_id = TRANSACTION_PROVIDER_CLASS.make_payout(
                self.customer_id, self.group_id,
                self.amount_cents)
            self.status = Status.COMPLETE
            self.external_id = external_id
            self.event = ActionCatalog.TR_EXECUTE_PAYOUT
        except Exception, e:
            self.status = Status.ERROR
            self.event = ActionCatalog.TR_PAYOUT_ERROR
            self.session.commit()
            raise e
        self.customer.charge_attempts = 0
        self.session.commit()

    __table_args__ = (
        # Customer foreign key
        ForeignKeyConstraint(
            [customer_id, group_id],
            [Customer.external_id, Customer.group_id]),
    )
