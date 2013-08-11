from __future__ import unicode_literals

from sqlalchemy import Column, Unicode, ForeignKey, Integer
from sqlalchemy.orm import relationship

from billy.models import Base
from billy.utils.models import uuid_factory, Enum


ChargeTransactionStatus = Enum('PENDING', 'SENT', 'ERROR',
                         name='charge_plan_transaction_status')


class ChargeTransaction(Base):
    __tablename__ = "charge_transactions"

    id = Column(Unicode, primary_key=True, default=uuid_factory('PAT'))
    customer_id = Column(Unicode,
                         ForeignKey('customers.id', ondelete='cascade'),
                         nullable=False)
    processor_txn_id = Column(Unicode, nullable=False)
    amount_cents = Column(Integer, nullable=False)
    status = Column(ChargeTransactionStatus, nullable=False)
    invoice_id = Column(Unicode, ForeignKey('charge_plan_invoices.id'),
                        nullable=False)

    @classmethod
    def create(cls, customer, amount_cents):
        transaction = cls(
            customer=customer,
            amount_cents=amount_cents,
            status=ChargeTransactionStatus.PENDING
        )
        try:
            processor_txn_id = transaction.customer.company.processor.create_charge(
                transaction.customer.processor_id, transaction.amount_cents)
            transaction.status = ChargeTransactionStatus.SENT
            transaction.processor_txn_id = processor_txn_id
            cls.session.add(transaction)
        except:
            transaction.status = ChargeTransactionStatus.ERROR
            cls.session.add(transaction)
            transaction.session.commit()
            raise
        return transaction