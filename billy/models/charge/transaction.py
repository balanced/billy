from __future__ import unicode_literals

from sqlalchemy import Column, Unicode, ForeignKey
from sqlalchemy.orm import relationship

from models import Base
from models.transactions import TransactionMixin, TransactionStatus
from utils.models import uuid_factory


class ChargeTransaction(TransactionMixin, Base):
    __tablename__ = "charge_transactions"

    id = Column(Unicode, primary_key=True, default=uuid_factory('PAT'))
    customer_id = Column(Unicode, ForeignKey('customers.id'), nullable=False)

    invoices = relationship('ChargePlanInvoice', backref='transaction',
                            cascade='delete')

    def execute(self):
        try:
            your_id = self.customer.company.processor.create_charge(
                self.customer.processor_id, self.amount_cents)
            self.status = TransactionStatus.COMPLETE
            self.your_id = your_id
        except:
            self.status = TransactionStatus.ERROR
            self.session.commit()
            raise