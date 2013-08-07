from datetime import datetime
from sqlalchemy import Column, Unicode, ForeignKey, DateTime, Boolean, Index
from models import Base, ChargePlan, Customer
from utils.models import uuid_factory


class ChargeSubscription(Base):
    __tablename__ = 'charge_subscription'

    id = Column(Unicode, primary_key=True, default=uuid_factory('CS'))
    customer_id = Column(Unicode, ForeignKey(Customer.id), nullable=False)
    plan_id = Column(Unicode, ForeignKey(ChargePlan.id), nullable=False)
    is_enrolled = Column(Boolean, default=True)
    should_renew = Column(Boolean, default=True)

    __table_args__ = (
        Index('unique_charge_sub', plan_id, customer_id,
              postgresql_where=should_renew == True,
              unique=True),
    )

    @classmethod
    def create(cls, customer, plan):
        result = cls.query.filter(
            cls.customer_id == customer.id,
            cls.plan_id == plan.id).first()
        result = result or cls(
            customer_id=customer.id, plan_id=plan.id,
            # Todo TEMP since default not working for some reason
            id=uuid_factory('PLS')())
        result.should_renew = True
        result.is_enrolled = True
        # Todo premature commit might cause issues....
        cls.session.add(result)
        return result

    @property
    def current_invoice(self):
        return self.invoices.filter(
            ChargePlanInvoice.end_dt > datetime.utcnow()).first()

    def cancel(self, cancel_at_period_end=False):
        if cancel_at_period_end:
            self.is_active = False
        else:
            return ChargePlanInvoice.prorate_last(self.customer, self.plan)
        return self
