from __future__ import unicode_literals
from datetime import datetime

from pytz import UTC
from sqlalchemy import Column, Unicode, Integer, Boolean, DateTime, \
    ForeignKey, UniqueConstraint
from sqlalchemy.orm import validates

from billy.models import *
from billy.models.base import RelativeDelta
from billy.utils.models import uuid_factory
from billy.utils.billy_action import ActionCatalog


class Payout(Base):
    __tablename__ = 'payouts'

    guid = Column(Unicode, index=True, default=uuid_factory('PO'))
    external_id = Column(Unicode, primary_key=True)
    group_id = Column(Unicode, ForeignKey(Group.external_id), primary_key=True)
    name = Column(Unicode)
    balance_to_keep_cents = Column(Integer)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=UTC), default=datetime.now(UTC))
    deleted_at = Column(DateTime(timezone=UTC))
    updated_at = Column(DateTime(timezone=UTC), default=datetime.now(UTC))
    payout_interval = Column(RelativeDelta)

    __table_args__ = (UniqueConstraint(external_id, group_id,
                                       name='plan_id_group_unique'),
    )


    @classmethod
    def create(cls, external_id, group_id, name,
               balance_to_keep_cents,
               payout_interval):
        """
        Creates a payout that users can be assigned to.
        :param external_id: A unique id/uri for the payout
        :param group_id: a group id/uri the user should be placed
        in (matches balanced payments group_id)
        :param name: A display name for the payout
        :param balance_to_keep_cents: The amount to keep in the users balance
        . Everything else will be paid out.
        :param payout_interval: A Interval class that defines how frequently the
        make the payout
        :return: Payout Object if success or raises error if not
        """
        new_payout = cls(
            external_id=external_id,
            group_id=group_id,
            name=name,
            balance_to_keep_cents=balance_to_keep_cents,
            payout_interval=payout_interval)
        new_payout.event = ActionCatalog.PAYOUT_CREATE
        cls.session.add(new_payout)
        cls.session.commit()
        return new_payout

    @classmethod
    def retrieve(cls, external_id, group_id, active_only=False):
        """
        This method retrieves a single payout.
        :param external_id: the unique external_id
        :param group_id: the payouts group
        :param active_only: if true only returns active payouts
        :raise NotFoundError:  if payout not found.
        """
        query = cls.query.filter(cls.external_id == external_id,
                           cls.group_id == group_id)
        if active_only:
            query = query.filter(cls.active == True)
        return query.one()

    def update(self, name):
        """
        Updates the payout's name
        :param name:
        :return: The updated Payout object (self)
        """
        self.name = name
        self.updated_at = datetime.now(UTC)
        self.event = ActionCatalog.PAYOUT_UPDATE
        self.session.commit()
        return self


    @classmethod
    def list(cls, group_id, active_only=False):
        """
        Returns a list of payouts currently in the database
        :param group_id: The group id/uri
        :returns: A list of Payout objects
        """
        query = cls.query.filter(cls.group_id == group_id)
        if active_only:
            query = query.filter(cls.active == True)
        return query.all()


    def delete(self):
        """
        This method deletes a payout. Payouts are not deleted from the
        database,
        but are instead marked as inactive so no new
        users can be added. Everyone currently on the Payout is maintained on
        the Payout.
        :returns: the deleted Payout object (self)
        """
        self.active = False
        self.updated_at = datetime.now(UTC)
        self.deleted_at = datetime.now(UTC)
        self.event = ActionCatalog.PAYOUT_DELETE
        self.session.commit()
        return self

    @validates('balance_to_keep_cents')
    def validate_balance_to_keep(self, key, address):
        if not address > 0:
            raise ValueError("balance_to_keep_cents must be greater than 0")
        return address
