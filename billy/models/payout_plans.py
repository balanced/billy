from __future__ import unicode_literals
from datetime import datetime

from sqlalchemy import Column, Unicode, Integer, Boolean, DateTime, \
    ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import relationship

from models import Base, Company, PayoutSubscription
from models.base import RelativeDelta
from utils.generic import uuid_factory


class PayoutPlan(Base):
    __tablename__ = 'payout_plans'

    guid = Column(Unicode, primary_key=True, default=uuid_factory('PO'))
    your_id = Column(Unicode, nullable=False)
    company_id = Column(Unicode, ForeignKey(Company.guid), nullable=False)
    name = Column(Unicode, nullable=False)
    balance_to_keep_cents = Column(Integer,
                                   CheckConstraint('balance_to_keep_cents >= 0'
                                                   ), nullable=False)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    deleted_at = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.utcnow)
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
        self.updated_at = datetime.utcnow()
        self.session.commit()
        return self

    def disable(self):
        """
        Disables a payout plan. Does not effect current subscribers.
        """
        self.active = False
        self.updated_at = datetime.utcnow()
        self.deleted_at = datetime.utcnow()
        self.session.commit()
        return self
