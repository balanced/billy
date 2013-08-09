from __future__ import unicode_literals
from datetime import datetime

from sqlalchemy import (Column, Unicode, Integer, Boolean,
                        ForeignKey, UniqueConstraint, CheckConstraint)
from sqlalchemy.orm import relationship

from models import Base, PayoutPlanInvoice, PayoutSubscription
from models.base import RelativeDelta
from utils.models import uuid_factory


class PayoutPlan(Base):
    __tablename__ = 'payout_plans'

    id = Column(Unicode, primary_key=True, default=uuid_factory('POP'))
    your_id = Column(Unicode, nullable=False)
    company_id = Column(Unicode, ForeignKey('companies.id', ondelete='cascade'),
                        nullable=False)
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

    def disable(self):
        """
        Disables a payout plan. Does not effect current subscribers.
        """
        self.is_active = False
        self.disabled_at = datetime.utcnow()
        return self

    def subscribe(self, customer, first_now=False, start_dt=None):
        first_charge = start_dt or datetime.utcnow()
        balance_to_keep_cents = self.balance_to_keep_cents
        if not first_now:
            first_charge += self.payout_interval
        subscription = PayoutSubscription.create(customer, self)
        invoice = PayoutPlanInvoice.create(subscription.id,
                                           first_charge,
                                           balance_to_keep_cents)
        self.session.add(invoice)
        return subscription