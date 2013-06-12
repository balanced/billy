from __future__ import unicode_literals
from datetime import datetime

from pytz import UTC
from sqlalchemy import Boolean, Column, DateTime, Integer, ForeignKey, \
    Unicode, UniqueConstraint
from sqlalchemy.orm import relationship, validates

from billy.models import *
from billy.utils.models import uuid_factory
from billy.utils.audit_events import EventCatalog


class Coupon(Base):
    __tablename__ = 'coupons'

    guid = Column(Unicode, primary_key=True, default=uuid_factory('CU'))
    external_id = Column(Unicode)
    group_id = Column(Unicode, ForeignKey(Group.external_id))
    name = Column(Unicode)
    price_off_cents = Column(Integer)
    percent_off_int = Column(Integer)
    expire_at = Column(DateTime(timezone=UTC))
    max_redeem = Column(Integer)
    repeating = Column(Integer)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=UTC), default=datetime.now(UTC))
    deleted_at = Column(DateTime(timezone=UTC))
    customers = relationship('Customer', backref='coupon')

    __table_args__ = (UniqueConstraint(external_id, group_id,
                                       name='coupon_id_group_unique'),
    )

    @classmethod
    def create(cls, external_id, group_id, name, price_off_cents,
                      percent_off_int, max_redeem, repeating, expire_at=None):
        """
        Creates a coupon that can be later applied to a customer.
        :param external_id: A unique id for the coupon
        :param group_id: The group uri/id this coupon is
        associated with
        :param name: A display name for the coupon
        :param price_off_cents: In CENTS the $ amount off on each invoice. $1
        .00 == 100
        :param percent_off_int: The percent to reduce off each invoice. 25%
        == 25
        :param expire_at: Datetime in which after the coupon will no longer work
        :param max_redeem: The number of unique users that can redeem this
        coupon, -1 for unlimited
        :param repeating: The maximum number of invoices it applies to. -1
        for all/forever
        :return: The new coupon object
        """
        new_coupon = cls(
            external_id=external_id,
            group_id=group_id,
            name=name,
            price_off_cents=price_off_cents,
            percent_off_int=percent_off_int,
            max_redeem=max_redeem,
            repeating=repeating,
            expire_at=expire_at)
        new_coupon.event = EventCatalog.COUPON_CREATE
        cls.session.add(new_coupon)
        cls.session.commit()
        return new_coupon

    @classmethod
    def retrieve(cls, external_id, group_id, active_only=False):
        """
        This method retrieves a single coupon.
        :param external_id: the unique external_id
        :param group_id: the group/marketplace to associate with
        :param active_only: only returns active coupons
        :returns: Single coupon
        """
        query = cls.query.filter(cls.external_id == external_id,
                           cls.group_id == group_id)
        if active_only:
            query = query.filter(cls.active == True)
        return query.one()

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
        self.updated_at = datetime.now(UTC)
        self.event = EventCatalog.COUPON_UPDATE
        self.session.commit()

    def delete(self):
        """
        Deletes the coupon. Coupons are not deleted from the database,
        but are instead marked as inactive so no
        new users can be added. Everyone currently on the coupon remain on the
        plan
        """
        self.active = False
        self.updated_at = datetime.now(UTC)
        self.deleted_at = datetime.now(UTC)
        self.event = EventCatalog.COUPON_DELETE
        self.session.commit()
        return self


    @classmethod
    def list(cls, group_id, active_only=False):
        """
        Returns a list of coupons currently in the database
        :param group_id: The group/marketplace id/uri
        :returns: A list of Coupon objects
        """
        query = cls.query.filter(cls.group_id == group_id)
        if active_only:
            query = query.filter(cls.active == True)
        return query.all()

    @property
    def count_redeemed(self):
        """
        The number of unique customers that are using the coupon
        """
        return Customer.query.filter(Customer.current_coupon == self
        .external_id).count()

    @classmethod
    def expire_coupons(cls):
        """
        Expires all expired coupons (TASK)
        """
        now = datetime.now(UTC)
        to_expire = cls.query.filter(cls.expire_at < now).all()
        for coupon in to_expire:
            coupon.active = False
            coupon.event = EventCatalog.COUPON_EXPIRE
        cls.session.commit()

    @validates('max_redeem')
    def validate_max_redeem(self, key, address):
        assert(address > 0 or address == -1)
        return address

    @validates('repeating')
    def validate_repeating(self, key, address):
        assert(address > 0 or address == -1)
        return address

    @validates('percent_off_int')
    def validate_percent_off_int(self, key, address):
        assert(0 < address <= 100)
        return address

    @validates('price_off_cents')
    def validate_price_off_cents(self, key, address):
        assert(address >= 0)
        return address