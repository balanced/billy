from __future__ import unicode_literals

from pytz import UTC
from sqlalchemy import Column, Unicode, ForeignKey, DateTime, Integer
from sqlalchemy.orm import relationship

from models import Base, Customer, ChargePlanInvoice, PayoutInvoice
from utils.generic import uuid_factory, Status


class TransactionMixin(object):
    provider_txn_id = Column(Unicode, nullable=False)
    created_at = Column(DateTime(timezone=UTC))
    amount_cents = Column(Integer, nullable=False)
    status = Column(Unicode, nullable=False)

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


class ChargeTransaction(TransactionMixin, Base):
    __tablename__ = "charge_transactions"

    guid = Column(Unicode, primary_key=True, default=uuid_factory('PAT'))
    customer_id = Column(Unicode, ForeignKey(Customer.guid), nullable=False)

    invoices = relationship(ChargePlanInvoice, backref='transaction',
                            cascade='delete')

    def execute(self):
        try:
            external_id = self.customer.company.processor_class.create_charge(
                self.customer.guid, self.customer.group_id,
                self.amount_cents)
            self.status = Status.COMPLETE
            self.external_id = external_id
        except:
            self.status = Status.ERROR
            self.session.commit()
            raise
        self.customer.charge_attempts = 0
        self.session.commit()


class PayoutTransaction(TransactionMixin, Base):
    __tablename__ = 'payout_transactions'

    guid = Column(Unicode, primary_key=True, default=uuid_factory('POT'))
    customer_id = Column(Unicode, ForeignKey(Customer.guid), nullable=False)

    invoices = relationship(PayoutInvoice,
                            backref='transaction', cascade='delete')

    def execute(self):
        try:
            external_id = self.customer.company.processor_class.make_payout(
                self.customer.guid, self.customer.group_id,
                self.amount_cents)
            self.status = Status.COMPLETE
            self.external_id = external_id
        except:
            self.status = Status.ERROR
            self.session.commit()
            raise
        self.session.commit()
