from billy.models.base import Base, JSONDict
from sqlalchemy import Column, String, Integer, Boolean, DateTime
from sqlalchemy.schema import UniqueConstraint, ForeignKey
from pytz import UTC
from datetime import datetime


class Customers(Base):
    __tablename__ = 'customers'

    customer_id = Column(String, primary_key=True)
    marketplace = Column(String)
    current_plan = Column(String, ForeignKey('plans.plan_id'))
    current_payout = Column(String, ForeignKey('payouts.payout_id'))
    current_coupon = Column(Integer, ForeignKey('coupons.coupon_id'))
    created_at = Column(DateTime(timezone=UTC), default=datetime.now(UTC))
    updated_at = Column(DateTime(timezone=UTC), default=datetime.now(UTC))
    periods_on_plan = Column(Integer)
    coupon_use = Column(JSONDict, default={})
    plan_use = Column(JSONDict, default={})

    __table_args__ = (UniqueConstraint('customer_id', 'marketplace', name='customerid_marketplace'),
    )


    def __init__(self, id, marketplace):
        self.customer_id = id
        self.marketplace = marketplace
