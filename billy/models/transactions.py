from __future__ import unicode_literals

from sqlalchemy import Column, Unicode, Integer

from utils.models import Enum

TransactionStatus = Enum('PENDING', 'COMPLETE', 'ERROR',
                          name='transaction_status')


class TransactionMixin(object):
    processor_txn_id = Column(Unicode, nullable=False)
    amount_cents = Column(Integer, nullable=False)
    status = Column(TransactionStatus, nullable=False)

    @classmethod
    def create(cls, customer_id, amount_cents):
        transaction = cls(
            customer_id=customer_id,
            amount_cents=amount_cents,
            status=TransactionStatus.PENDING
        )
        cls.session.add(transaction)
        return transaction


