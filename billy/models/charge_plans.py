from __future__ import unicode_literals
from datetime import datetime

from sqlalchemy import (Column, Unicode, Integer, Boolean, DateTime,
                        ForeignKey, UniqueConstraint, CheckConstraint)
from sqlalchemy.orm import relationship

from models import Base, Company
from models.base import RelativeDelta
from utils.generic import uuid_factory


class ChargePlan(Base):
    __tablename__ = 'charge_plans'

    id = Column(Unicode, primary_key=True, default=uuid_factory('PL'))
    your_id = Column(Unicode, nullable=False)
    company_id = Column(Unicode, ForeignKey(Company.id), nullable=False)
    name = Column(Unicode, nullable=False)
    price_cents = Column(Integer, CheckConstraint('price_cents >= 0'),
                         nullable=False)
    active = Column(Boolean, default=True)
    disabled_at = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.utcnow)
    trial_interval = Column(RelativeDelta)
    plan_interval = Column(RelativeDelta)

    subscriptions = relationship('ChargeSubscription', backref='plan',
                                 cascade='delete, delete-orphan')

    __table_args__ = (UniqueConstraint(your_id, company_id,
                                       name='plan_id_company_unique'),
                      )

    def update(self, name):
        """
        Updates the name of a plan
        """
        self.name = name
        return self

    def disable(self):
        """
        Disables a charge plan. Does not effect current subscribers.
        """
        self.active = False
        self.disabled_at = datetime.utcnow()
        return self

    def can_customer_trial(self, customer):
        """
        Whether a customer can trial a charge plan
        """
        from models import ChargeSubscription
        return ChargeSubscription.query.filter(
            ChargeSubscription.customer_id == customer.id,
            ChargeSubscription.plan_id == self.id
        ).first()
