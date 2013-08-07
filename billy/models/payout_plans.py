from __future__ import unicode_literals
from datetime import datetime

from sqlalchemy import (Column, Unicode, Integer, Boolean,
    ForeignKey, UniqueConstraint, CheckConstraint)
from sqlalchemy.orm import relationship

from models import Base, Company
from models.base import RelativeDelta
from utils.generic import uuid_factory


class PayoutPlan(Base):
    __tablename__ = 'payout_plans'

    id = Column(Unicode, primary_key=True, default=uuid_factory('PO'))
    your_id = Column(Unicode, nullable=False)
    company_id = Column(Unicode, ForeignKey(Company.id), nullable=False)
    name = Column(Unicode, nullable=False)
    balance_to_keep_cents = Column(Integer,
                                   CheckConstraint('balance_to_keep_cents >= 0'
                                                   ), nullable=False)
    is_active = Column(Boolean, default=True)
    payout_interval = Column(RelativeDelta, nullable=False)

    subscriptions = relationship('PayoutSubscription', backref='payout',
                                 cascade='delete, delete-orphan')

    __table_args__ = (UniqueConstraint(your_id, company_id,
                                       name='payout_id_group_unique'),
                      )

    def update(self, name):
        """
        Update the payout plan's names
        """
        self.name = name
        return self

    def disable(self):
        """
        Disables a payout plan. Does not effect current subscribers.
        """
        self.is_active = False
        self.disabled_at = datetime.utcnow()
        return self
