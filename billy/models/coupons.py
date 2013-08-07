from __future__ import unicode_literals
from datetime import datetime

from sqlalchemy import (Boolean, Column, DateTime, Integer, ForeignKey,
                        Unicode, UniqueConstraint, CheckConstraint)
from sqlalchemy.orm import relationship

from models import Base
from utils.models import uuid_factory


class Coupon(Base):
    __tablename__ = 'coupons'

    id = Column(Unicode, primary_key=True, default=uuid_factory('CU'))
    your_id = Column(Unicode, nullable=False)
    company_id = Column(Unicode, ForeignKey('companies.id'), nullable=False)
    name = Column(Unicode, nullable=False)
    price_off_cents = Column(Integer, CheckConstraint('price_off_cents >= 0'))
    percent_off_int = Column(Integer, CheckConstraint(
        'percent_off_int >= 0 OR percent_off_int <= 100'))
    expire_at = Column(DateTime)
    max_redeem = Column(Integer,
                        CheckConstraint('max_redeem = -1 OR max_redeem >= 0'))
    repeating = Column(Integer,
                       CheckConstraint('repeating = -1 OR repeating >= 0'))
    active = Column(Boolean, default=True)
    disabled_at = Column(DateTime)

    customers = relationship('Customer', backref='coupon', lazy='dynamic')

    __table_args__ = (
        UniqueConstraint(your_id, company_id,
                         name='coupon_id_group_unique'),
    )

    def redeem(self, customer):
        """
        Applies the coupon to a customer
        """
        if self.max_redeem != -1 and self.count_customers >= \
                self.max_redeem:
            raise ValueError('Coupon already redeemed maximum times. See '
                             'max_redeem')
        customer.current_coupon = self.id
        return self

    def update(self, new_name=None,
               new_max_redeem=None, new_expire_at=None, new_repeating=None):
        """
        Updates the coupon with new information provided.
        :param new_name: A display name for the coupon
        :param new_max_redeem: The number of unique users that can redeem
        this coupon
        :param new_expire_at: Datetime in which after the coupon will no longer
        work
        :param new_repeating: The maximum number of invoices it applies to.
        -1 for all/forever
        :returns: Self
        """
        if new_name:
            self.name = new_name
        if new_max_redeem:
            self.max_redeem = new_max_redeem
        if new_expire_at:
            self.expire_at = new_expire_at
        if new_repeating:
            self.repeating = new_repeating
        return self

    def disable(self):
        """
        Deletes the coupon. Coupons are not deleted from the database,
        but are instead marked as inactive so no
        new users can be added. Everyone currently on the coupon remain on the
        plan
        """
        self.active = False
        self.disabled_at = datetime.utcnow()
        return self

    @property
    def count_customers(self):
        """
        The number of unique customers that are using the coupon
        """
        return self.customer.count()

    @classmethod
    def expire_coupons(cls):
        """
        Expires all expired coupons (TASK)
        """
        now = datetime.utcnow()
        to_expire = cls.query.filter(cls.expire_at < now).all()
        for coupon in to_expire:
            coupon.active = False
