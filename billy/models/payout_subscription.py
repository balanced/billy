from datetime import datetime
from sqlalchemy import Column, Unicode, ForeignKey, DateTime, Boolean, Index
from models import Base, Customer, PayoutPlan
from utils.generic import uuid_factory


class PayoutSubscription(Base):
    __tablename__ = 'payout_subscription'

    guid = Column(Unicode, primary_key=True, default=uuid_factory('POS'))
    customer_id = Column(Unicode, ForeignKey(Customer.guid), nullable=False)
    payout_id = Column(Unicode, ForeignKey(PayoutPlan.guid), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    __table_args__ = (
        Index('unique_payout_sub', payout_id, customer_id,
              postgresql_where=is_active == True,
              unique=True),
    )

    @classmethod
    def create(cls, customer, payout):
        result = cls.query.filter(
            cls.customer_id == customer.guid,
            cls.payout_id == payout.guid).first()
        result = result or cls(
            customer_id=customer.guid, payout_id=payout.guid,
            # Todo Temp since default not working for some reason
            guid=uuid_factory('PLL')())
        result.is_active = True
        cls.session.add(result)
        # Todo premature commit might cause issues....
        cls.session.commit()
        return result


    def cancel(self, cancel_scheduled=False):
        from models import PayoutInvoice

        self.is_active = False
        if cancel_scheduled:
            in_process = self.invoices.filter(
                PayoutInvoice.completed == False).first()
            if in_process:
                in_process.completed = True
        self.session.commit()
        return self