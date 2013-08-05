from __future__ import unicode_literals
from datetime import datetime

from sqlalchemy import Column, Unicode, Integer, Boolean, DateTime, \
    ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import relationship

from models import *
from models.base import RelativeDelta
from utils.generic import uuid_factory


class PayoutPlan(Base):
    __tablename__ = 'payout_plans'

    guid = Column(Unicode, primary_key=True, default=uuid_factory('PO'))
    external_id = Column(Unicode, nullable=False)
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
                                 cascade='delete')

    __table_args__ = (UniqueConstraint(external_id, company_id,
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

    def subscribe(self, customer, first_now=False, start_dt=None):
        from models import PayoutSubscription

        first_charge = start_dt or datetime.utcnow()
        balance_to_keep_cents = self.balance_to_keep_cents
        if not first_now:
            first_charge += self.payout_interval
        new_sub = PayoutSubscription.create_or_activate(customer, self)
        invoice = PayoutInvoice.create(new_sub.guid,
                                       first_charge,
                                       balance_to_keep_cents,
        )
        self.session.add(invoice)
        try:
            self.session.commit()
        except:
            self.session.rollback()
            raise
        return invoice

    def unsubscribe(self, customer, cancel_scheduled=False):
        from models import PayoutSubscription, PayoutInvoice

        current_sub = PayoutSubscription.query.filter(
            PayoutSubscription.customer_id == customer.guid,
            PayoutSubscription.payout_id == self.guid,
            PayoutSubscription.is_active == True).first()
        if current_sub:
            current_sub.is_active = False
            if cancel_scheduled:
                in_process = current_sub.invoices.filter(
                    PayoutInvoice.completed == False).first()
                if in_process:
                    in_process.completed = True
            cls.session.commit()
        return True

