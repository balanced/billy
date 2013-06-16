from __future__ import unicode_literals

from sqlalchemy import Unicode, Column
from sqlalchemy.orm import relationship

from base import Base
from billy.utils.billy_action import ActionCatalog


class Group(Base):
    __tablename__ = 'groups'

    external_id = Column(Unicode, primary_key=True)
    coupons = relationship('BillyAction', backref='group')
    customers = relationship('Customer', backref='group')
    plans = relationship('Plan', backref='group')
    payouts = relationship('Payout', backref='group')
    plan_invoices = relationship('PlanInvoice', backref='group')
    payout_invoices = relationship('PayoutInvoice', backref='group')

    @classmethod
    def create_group(cls, external_id):
        new_group = cls(external_id=external_id)
        new_group.event = ActionCatalog.GROUP_CREATE
        cls.session.add(new_group)
        cls.session.commit()
        return new_group

    @classmethod
    def retrieve_group(cls, external_id):
        # Used one() instead get() to raise error if not found...
        return cls.query.filter(cls.external_id == external_id).one()
