from __future__ import unicode_literals

from sqlalchemy import Column, Unicode, ForeignKey
from sqlalchemy.orm import relationship

from models import Base
from models.transactions import TransactionMixin
from utils.models import uuid_factory


class PayoutTransaction(TransactionMixin, Base):
    __tablename__ = 'payout_transactions'

    id = Column(Unicode, primary_key=True, default=uuid_factory('POT'))
    customer_id = Column(Unicode, ForeignKey('customers.id'), nullable=False)

    invoices = relationship('PayoutPlanInvoice',
                            backref='transaction', cascade='delete')

    def execute(self):
        try:
            your_id = self.customer.company.processor.make_payout(
                self.customer.processor_id, self.amount_cents)
            self.status = 'COMPLETE'
            self.your_id = your_id
        except:
            self.status = 'ERROR'
            self.session.commit()
            raise