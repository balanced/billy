from billy.models.base import Base
from sqlalchemy import Column, String, Integer, Boolean, DateTime
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.orm import relationship
from pytz import UTC
from datetime import datetime
from billy.customer.models import Customers
from billy.invoices.models import ChargeInvoice


class Coupon(Base):
    __tablename__ = 'coupons'

    coupon_id = Column(String, primary_key=True)
    name = Column(String)
    marketplace = Column(String)
    price_off_cents = Column(Integer)
    percent_off_int = Column(Integer)
    expire = Column(DateTime(timezone=UTC))
    times_used = Column(Integer)
    max_redeem = Column(Integer) #Count different users who can redeeem it
    repeating = Column(
        Integer) # -1 = Forever, int = Number of invoices  per user
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=UTC), default=datetime.now(UTC))
    deleted_at = Column(DateTime(timezone=UTC))
    customers = relationship(Customers, backref='coupons')
    __table_args__ = (
    UniqueConstraint('coupon_id', 'marketplace', name='couponid_marketplace'),
    )


    def __init__(self, id, marketplace, name, percent_off_cents,
                 percent_off_int, expire, max_redeem, repeating):
        self.coupon_id = id
        self.marketplace = marketplace
        self.name = name
        self.price_off_cents = percent_off_cents
        self.percent_off_int = percent_off_int
        self.expire = expire
        self.times_used = 0
        self.max_redeem = max_redeem
        self.repeating = repeating

