from __future__ import unicode_literals

from sqlalchemy import Column, Unicode, ForeignKey, DateTime, Boolean, Index

from models import Base
from utils.models import uuid_factory


class PayoutSubscription(Base):
    __tablename__ = 'payout_subscription'

    id = Column(Unicode, primary_key=True, default=uuid_factory('PS'))
    customer_id = Column(Unicode, ForeignKey('customers.id'), nullable=False)
    payout_id = Column(Unicode, ForeignKey('payout_plans.id'), nullable=False)
    is_active = Column(Boolean, default=True)

    __table_args__ = (
        Index('unique_payout_sub', payout_id, customer_id,
              postgresql_where=is_active == True,
              unique=True),
    )

    @classmethod
    def create(cls, customer, payout):
        result = cls.query.filter(
            cls.customer_id == customer.id,
            cls.payout_id == payout.id).first()
        result = result or cls(
            customer_id=customer.id, payout_id=payout.id,
            # Todo Temp since default not working for some reason
            id=uuid_factory('PLL')())
        result.is_active = True
        cls.session.add(result)
        return result

    def cancel(self, cancel_scheduled=False):
        from models import PayoutInvoice
        self.is_active = False
        if cancel_scheduled:
            in_process = self.invoices.filter(
                PayoutInvoice.completed == False).first()
            if in_process:
                in_process.completed = True
        return self
