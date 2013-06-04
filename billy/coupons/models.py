from billy.models.base import Base
from sqlalchemy import and_
from sqlalchemy import Column, String, Integer, Boolean, DateTime
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.orm import relationship
from pytz import UTC
from datetime import datetime
from billy.customer.models import Customer
from billy.errors import NotFoundError, AlreadyExistsError
from datetime import datetime
from pytz import UTC

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

    @classmethod
    def create_coupon(cls, coupon_id, marketplace, name, price_off_cents,
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

        exists = cls.query.filter(and_(Coupon.coupon_id == coupon_id,
                                          Coupon.marketplace == marketplace)).first()
        if not exists:
            new_coupon = Coupon(coupon_id, marketplace, name, price_off_cents,
                                percent_off_int, max_redeem, repeating, expire)
            cls.session.add(new_coupon)
            cls.session.commit()
            return new_coupon
        else:
            raise AlreadyExistsError('Coupon already exists. Check coupon_id and marketplace')

    @classmethod
    def retrieve_coupon(cls, coupon_id, marketplace, active_only=False):
        """
        This method retrieves a single coupon.
        :param coupon_id: the unique coupon_id
        :param marketplace: the coupon marketplace/group
        :param active_only: only returns active coupons
        :returns: Single coupon
        :raise NotFoundError:  if coupon not found.
        """
        if active_only:
            and_filter = and_(Coupon.coupon_id == coupon_id,
                              Coupon.marketplace == marketplace,
                              Coupon.active == True)
        else:
            and_filter = and_(Coupon.coupon_id == coupon_id, Coupon.marketplace == marketplace)
        exists = cls.query.filter(and_filter).first()
        if not exists:
            raise NotFoundError('Active Coupon not found. Check coupon_id and marketplace')
        return exists

    @classmethod
    def update_coupon(cls, coupon_id, marketplace, new_name=None,
                      new_max_redeem=None, new_expire=None, new_repeating=None):
        """
        Updates the coupon information, by design only the params listed are updatable and
        effect future charges.
        :param coupon_id: A unique id for the coupon
        :param marketplace: The marketplace/group uri/id this coupon is associated with
        :param new_name: A display name for the coupon
        :param new_max_redeem: The number of unique users that can redeem this coupon
        :param new_expire: Datetime in which after the coupon will no longer work
        :param new_repeating: The maximum number of invoices it applies to. -1 for all/forever
        :raise NotFoundError:  if coupon not found.
        :returns: New coupon object
        """
        #Todo update active if max_redeem below/above times_used
        exists = cls.query.filter(and_(cls.coupon_id == coupon_id,
                                      cls.marketplace == marketplace)).first()
        if not exists:
            raise NotFoundError('Coupon not found. Use different id/marketplace')
        else:
            if new_name:
                exists.name = new_name
            if new_max_redeem:
                exists.max_redeem = new_max_redeem
            if new_expire:
                exists.expire = new_expire
            if new_repeating:
                exists.repeating = new_repeating
            exists.updated_at = datetime.now(UTC)
            cls.session.commit()
            return exists

    @classmethod
    def delete_coupon(cls, coupon_id, marketplace):
        """
        This method deletes a coupon. Coupons are not deleted from the database, but are instead marked as inactive so no
        new users can be added. Everyone currently on the plan
        :param coupon_id: the unique coupon_id
        :param marketplace: the plans marketplace/group
        :returns: the deleted Coupon object
        :raise NotFoundError:  if coupon not found.
        """
        exists = cls.query.filter(and_(Coupon.coupon_id == coupon_id,
                                     Coupon.marketplace == marketplace))\
            .first()
        if not exists:
            raise NotFoundError('Coupon not found. Try a different id')
        exists.active = False
        exists.updated_at = datetime.now(UTC)
        exists.deleted_at = datetime.now(UTC)
        cls.session.commit()
        return exists

    @classmethod
    def list_coupons(cls, marketplace):
        #Todo active only
        """
        Returns a list of coupons currently in the database
        :param marketplace: The group/marketplace id/uri
        :returns: A list of Coupon objects
        """
        results = cls.query.filter(Coupon.marketplace == marketplace).all()
        return results


    @property
    def count_redeemed(self):
        """
        The number of unique customers that are using the coupon
        """
        return Customer.query.filter(Customer.current_coupon == self
        .coupon_id).count()