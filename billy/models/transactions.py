from __future__ import unicode_literals

from pytz import UTC
from sqlalchemy import Column, Unicode, ForeignKey, DateTime, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.schema import ForeignKeyConstraint

from billy.models import Base, Group, Customer, PlanInvoice, PayoutInvoice
from billy.utils.generic import uuid_factory, Status
from billy.settings import TRANSACTION_PROVIDER_CLASS


class TransactionMixin(object):
    group_id = Column(Unicode, ForeignKey(Group.guid))
    customer_id = Column(Unicode, ForeignKey(Customer.guid))
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
    plan_invoices = relationship(PlanInvoice, backref='transaction')

    def execute(self):
        try:
            external_id = TRANSACTION_PROVIDER_CLASS.create_charge(
                self.customer_id, self.group_id,
                self.amount_cents)
            self.status = Status.COMPLETE
            self.external_id = external_id
        except Exception, e:
            self.status = Status.ERROR
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

    guid = Column(Unicode, primary_key=True, default=uuid_factory('POT'))
    payout_invoices = relationship(PayoutInvoice,
                                   backref='transaction')


    def execute(self):
        try:
            external_id = TRANSACTION_PROVIDER_CLASS.make_payout(
                self.customer_id, self.group_id,
                self.amount_cents)
            self.status = Status.COMPLETE
            self.external_id = external_id
        except Exception, e:
            self.status = Status.ERROR
            self.session.commit()
            raise e
        self.session.commit()

    __table_args__ = (
        # Customer foreign key
        ForeignKeyConstraint(
            [customer_id, group_id],
            [Customer.external_id, Customer.group_id]),
    )
