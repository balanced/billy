from __future__ import unicode_literals
from datetime import datetime

from pytz import UTC
from sqlalchemy import Boolean, Column, DateTime, Integer, ForeignKey, \
    Unicode, UniqueConstraint
from sqlalchemy.orm import relationship, validates

from models import *
from utils.generic import uuid_factory


class Coupon(Base):
    __tablename__ = 'coupons'

    guid = Column(Unicode, primary_key=True, default=uuid_factory('CU'))
    external_id = Column(Unicode, nullable=False)
    company_id = Column(Unicode, ForeignKey(Company.guid), nullable=False)
    name = Column(Unicode, nullable=False)
    price_off_cents = Column(Integer)
    percent_off_int = Column(Integer)
    expire_at = Column(DateTime(timezone=UTC))
    max_redeem = Column(Integer)
    repeating = Column(Integer)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=UTC), default=datetime.utcnow)
    deleted_at = Column(DateTime(timezone=UTC))

    customers = relationship('Customer', backref='coupon', lazy='dynamic')

    __table_args__ = (
        UniqueConstraint(external_id, company_id,
                         name='coupon_id_group_unique'),
    )


    def redeem(self, customer):
        """
        Applies the coupon to a customer
        """
        if self.max_redeem != -1 and self.count_redeemed >= \
                self.max_redeem:
            raise ValueError('Coupon already redeemed maximum times. See '
                             'max_redeem')
        customer.current_coupon = self.guid
        customer.updated_at = datetime.utcnow()
        self.session.commit()
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
        self.updated_at = datetime.utcnow()
        self.session.commit()
        return self

    def disable(self):
        """
        Deletes the coupon. Coupons are not deleted from the database,
        but are instead marked as inactive so no
        new users can be added. Everyone currently on the coupon remain on the
        plan
        """
        self.active = False
        self.updated_at = datetime.utcnow()
        self.deleted_at = datetime.utcnow()
        self.session.commit()
        return self

    @property
    def count_redeemed(self):
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
        cls.session.commit()

    @validates('max_redeem')
    def validate_max_redeem(self, key, address):
        if not (address > 0 or address == -1):
            raise ValueError('400_MAX_REDEEM')
        return address

    @validates('repeating')
    def validate_repeating(self, key, address):
        if not (address > 0 or address == -1):
            raise ValueError('400_REPEATING')
        return address

    @validates('percent_off_int')
    def validate_percent_off_int(self, key, address):
        if not 0 <= address <= 100:
            raise ValueError('400_PERCENT_OFF_INT')
        return address

    @validates('price_off_cents')
    def validate_price_off_cents(self, key, address):
        if not address >= 0:
            raise ValueError('400_PRICE_OFF_CENTS')
        return address
