from __future__ import unicode_literals

from sqlalchemy import Unicode, Column
from sqlalchemy.orm import relationship

from billy.models import Base
from billy.utils.generic import api_key_factory, uuid_factory

class Group(Base):
    __tablename__ = 'groups'

    guid = Column(Unicode, primary_key=True, default=uuid_factory('GR'))
    external_id = Column(Unicode, unique=True)
    api_key = Column(Unicode, unique=True, default=api_key_factory)
    coupons = relationship('Coupon', backref='group')
    customers = relationship('Customer', backref='group')
    plans = relationship('Plan', backref='group')
    payouts = relationship('Payout', backref='group')
    plan_invoices = relationship('PlanInvoice', backref='group')
    payout_invoices = relationship('PayoutInvoice', backref='group')

    @classmethod
    def create(cls, external_id, **kwargs):
        new_group = cls(external_id=external_id, **kwargs)
        cls.session.add(new_group)
        cls.session.commit()
        return new_group

    @classmethod
    def retrieve(cls, external_id):
        # Used one() instead get() to raise error if not found...
        return cls.query.filter(cls.external_id == external_id).one()
