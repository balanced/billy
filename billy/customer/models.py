from billy.models.base import Base
from sqlalchemy import Column, String, Integer, Boolean, DateTime
from sqlalchemy.schema import UniqueConstraint, ForeignKey
from pytz import UTC
from datetime import datetime


class Customer(Base):
    __tablename__ = 'coupons'

    customer_id = Column(String, primary_key=True)
    marketplace = Column(String)
    current_plan = Column(String, ForeignKey('plans.plan_id'))
    current_coupon = Column(Integer, ForeignKey('coupons.coupon_id'))
    created_at = Column(DateTime(timezone=UTC), default=datetime.now(UTC))


    __table_args__ = (UniqueConstraint('customer_id', 'marketplace', name='customerid_marketplace'),
    )


    def __init__(self, id, marketplace, plan_id, coupon_id):
        self.customer_id = id
        self.marketplace = marketplace
        self.plan_id = plan_id
        self.coupon_id = coupon_id
