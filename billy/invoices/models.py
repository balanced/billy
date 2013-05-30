from billy.models.base import Base
from sqlalchemy import Column, String, Integer, Boolean, DateTime
from sqlalchemy.types import DECIMAL
from sqlalchemy.schema import UniqueConstraint, ForeignKey
from pytz import UTC
from datetime import datetime

class Invoice(Base):
    __tablename__ = 'invoices'

    invoice_id = Column(Integer, primary_key=True)
    customer_id = Column(String, ForeignKey('customer.customer_id'))
    marketplace = Column(String)
    relevant_plan = Column(String, ForeignKey('plans.plan_id'))
    relevant_coupon = Column(Integer, ForeignKey('coupons.coupon_id'))
    created_at = Column(DateTime(timezone=UTC), default=datetime.now(UTC))
    start_date = Column(DateTime(timezone=UTC))
    end_date = Column(DateTime(timezone=UTC))
    due_on = Column(DateTime(timezone=UTC))
    amount_due = Column(DECIMAL)




    def __init__(self, id, marketplace, plan_id, coupon_id):
        self.customer_id = id
        self.marketplace = marketplace
        self.plan_id = plan_id
        self.coupon_id = coupon_id