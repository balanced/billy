from billy.models.base import Base
from sqlalchemy import Column, String, Integer, Boolean, DateTime
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.orm import relationship
from pytz import UTC
from datetime import datetime
from billy.customer.models import Customer


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
    count_redeemed = Column(Integer)
    customers = relationship(Customer, backref='coupon')
    __table_args__ = (
    UniqueConstraint('coupon_id', 'marketplace', name='couponid_marketplace'),
    )


    def __init__(self, id, marketplace, name, percent_off_cents,
                 percent_off_int, max_redeem, repeating, expire=None):
        self.coupon_id = id
        self.marketplace = marketplace
        self.name = name
        self.price_off_cents = percent_off_cents
        self.percent_off_int = percent_off_int
        self.expire = expire
        self.times_used = 0
        self.max_redeem = max_redeem
        self.repeating = repeating

    @staticmethod
    def create_coupon(coupon_id, marketplace, name, price_off_cents,
                      percent_off_int, max_redeem, repeating, expire=None):
        """
        Creates a coupon that can be later applied to a customer.
        :param coupon_id: A unique id for the coupon
        :param marketplace: The marketplace/group uri/id this coupon is associated with
        :param name: A display name for the coupon
        :param price_off_cents: In CENTS the $ amount off on each invoice. $1.00 == 100
        :param percent_off_int: The percent to reduce off each invoice. 25% == 25
        :param expire: Datetime in which after the coupon will no longer work
        :param max_redeem: The number of unique users that can redeem this
        coupon, -1 for unlimited
        :param repeating: The maximum number of invoices it applies to. -1 for all/forver
        :return: The new coupon object
        :raise AlreadyExistsError: If the coupon already exists
        """
    exists = Coupon.query.filter(and_(Coupon.coupon_id == coupon_id,
                                      Coupon.marketplace == marketplace)).first()
    if not exists:
        new_coupon = Coupon(coupon_id, marketplace, name, price_off_cents,
                            percent_off_int, max_redeem, repeating, expire)
        query_tool.add(new_coupon)
        query_tool.commit()
        return new_coupon
    else:
        raise AlreadyExistsError('Coupon already exists. Check coupon_id and marketplace')

    @property
    def count_redeemed(self):
        return Customer.query.filter(Customer.current_coupon == self
        .coupon_id).count()