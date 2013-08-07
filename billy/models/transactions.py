from __future__ import unicode_literals

from sqlalchemy import Column, Unicode, ForeignKey, DateTime, Integer, Enum
from sqlalchemy.orm import relationship

from models import Base, Customer, ChargePlanInvoice, PayoutInvoice
from utils.generic import uuid_factory

transaction_status = Enum('PENDING', 'COMPLETE', 'ERROR',
                          name='transaction_status')


class TransactionMixin(object):
    provider_txn_id = Column(Unicode, nullable=False)
    amount_cents = Column(Integer, nullable=False)
    status = Column(transaction_status, nullable=False)

    @classmethod
    def create(cls, customer_id, amount_cents):
        new_transaction = cls(
            customer_id=customer_id,
            amount_cents=amount_cents,
            status='PENDING'
        )
        cls.session.add(new_transaction)
        return new_transaction


class ChargeTransaction(TransactionMixin, Base):
    __tablename__ = "charge_transactions"

    id = Column(Unicode, primary_key=True, default=uuid_factory('PAT'))
    customer_id = Column(Unicode, ForeignKey(Customer.id), nullable=False)

    invoices = relationship(ChargePlanInvoice, backref='transaction',
                            cascade='delete')

    def execute(self):
        try:
            your_id = self.customer.company.processor.create_charge(
                self.customer.id, self.customer.group_id,
                self.amount_cents)
            self.status = 'COMPLETE'
            self.your_id = your_id
        except:
            self.status = 'ERROR'
            self.session.commit()
            raise
        self.customer.charge_attempts = 0


class PayoutTransaction(TransactionMixin, Base):
    __tablename__ = 'payout_transactions'

    id = Column(Unicode, primary_key=True, default=uuid_factory('POT'))
    customer_id = Column(Unicode, ForeignKey(Customer.id), nullable=False)

    invoices = relationship(PayoutInvoice,
                            backref='transaction', cascade='delete')

    def execute(self):
        try:
            your_id = self.customer.company.processor.make_payout(
                self.customer.id, self.customer.group_id,
                self.amount_cents)
            self.status = 'COMPLETE'
            self.your_id = your_id
        except:
            self.status = 'ERROR'
            self.session.commit()
            raise
