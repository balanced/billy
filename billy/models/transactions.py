from __future__ import unicode_literals

from pytz import UTC
from sqlalchemy import Column, Unicode, ForeignKey, DateTime, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.schema import ForeignKeyConstraint

from models import Base, Group, Customer, PlanInvoice, PayoutInvoice
from utils.generic import uuid_factory, Status
from settings import TRANSACTION_PROVIDER_CLASS


class TransactionMixin(object):
    provider_txn_id = Column(Unicode)
    created_at = Column(DateTime(timezone=UTC))
    amount_cents = Column(Integer)
    status = Column(Unicode)

    @classmethod
    def create(cls, customer_id, amount_cents):
        new_transaction = cls(
            customer_id=customer_id,
            amount_cents=amount_cents,
            status=Status.PENDING
        )
        cls.session.add(new_transaction)
        cls.session.commit()
        return new_transaction


class PlanTransaction(TransactionMixin, Base):
    __tablename__ = "plan_transactions"

    guid = Column(Unicode, primary_key=True, default=uuid_factory('PAT'))
    customer_id = Column(Unicode, ForeignKey(Customer.guid))

    plan_invoices = relationship(PlanInvoice, backref='transaction')

    def execute(self):
            try:
                external_id = TRANSACTION_PROVIDER_CLASS.create_charge(
                    self.customer.guid, self.customer.group_id,
                    self.amount_cents)
                self.status = Status.COMPLETE
                self.external_id = external_id
            except Exception, e:
                self.status = Status.ERROR
                self.session.commit()
                raise e
            self.customer.charge_attempts = 0
            self.session.commit()


class PayoutTransaction(TransactionMixin, Base):
    __tablename__ = 'payout_transactions'

    guid = Column(Unicode, primary_key=True, default=uuid_factory('POT'))
    customer_id = Column(Unicode, ForeignKey(Customer.guid))

    payout_invoices = relationship(PayoutInvoice,
                                   backref='transaction')

    def execute(self):
        try:
            external_id = TRANSACTION_PROVIDER_CLASS.make_payout(
                self.customer.guid, self.customer.group_id,
                self.amount_cents)
            self.status = Status.COMPLETE
            self.external_id = external_id
        except Exception, e:
            self.status = Status.ERROR
            self.session.commit()
            raise e
        self.session.commit()
