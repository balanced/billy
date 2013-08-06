from datetime import datetime
from sqlalchemy import Column, Unicode, ForeignKey, DateTime, Boolean, Index
from models import Base, Customer, ChargePlan
from utils.generic import uuid_factory


class ChargeSubscription(Base):
    __tablename__ = 'charge_subscription'

    guid = Column(Unicode, primary_key=True, default=uuid_factory('PLS'))
    customer_id = Column(Unicode, ForeignKey(Customer.guid), nullable=False)
    plan_id = Column(Unicode, ForeignKey(ChargePlan.guid), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
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
            cls.customer_id == customer.guid,
            cls.plan_id == plan.guid).first()
        result = result or cls(
            customer_id=customer.guid, plan_id=plan.guid,
            # Todo TEMP since default not working for some reason
            guid=uuid_factory('PLS')())
        result.should_renew = True
        result.is_enrolled = True
        # Todo premature commit might cause issues....
        cls.session.add(result)
        cls.session.commit()
        return result


    def cancel(self, cancel_at_period_end=False):
        from models import ChargePlanInvoice
        if cancel_at_period_end:
            self.is_active = False
        else:
            return ChargePlanInvoice.prorate_last(self.customer, self.plan)
        return self