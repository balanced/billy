from __future__ import unicode_literals

from sqlalchemy import Column, Unicode, ForeignKey, Integer
from sqlalchemy.orm import relationship

from models import Base
from utils.models import uuid_factory, Enum

PayoutTransactionStatus = Enum('PENDING', 'SENT', 'ERROR',
                         name='payout_plan_transaction_status')


class PayoutTransaction(Base):
    __tablename__ = 'payout_transactions'

    id = Column(Unicode, primary_key=True, default=uuid_factory('POT'))
    customer_id = Column(Unicode,
                         ForeignKey('customers.id', ondelete='cascade'),
                         nullable=False)
    processor_txn_id = Column(Unicode, nullable=False)
    amount_cents = Column(Integer, nullable=False)
    status = Column(PayoutTransactionStatus, nullable=False)

    invoices = relationship('PayoutPlanInvoice',
                            backref='transaction', cascade='delete')


    @classmethod
    def create(cls, customer, amount_cents):
        transaction = cls(
            customer=customer,
            amount_cents=amount_cents,
            status=PayoutTransactionStatus.PENDING
        )
        try:
            processor_txn_id = transaction.customer.company.processor.make_payout(
                transaction.customer.processor_id, transaction.amount_cents)
            transaction.status = PayoutTransactionStatus.SENT
            transaction.processor_txn_id = processor_txn_id
            cls.session.add(transaction)
        except:
            transaction.status = PayoutTransactionStatus.ERROR
            cls.session.add(transaction)
            transaction.session.commit()
            raise
        return transaction