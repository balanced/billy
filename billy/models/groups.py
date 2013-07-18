from __future__ import unicode_literals

from sqlalchemy import Unicode, Column
from sqlalchemy.orm import relationship

from billy.models import Base


class Group(Base):
    __tablename__ = 'groups'

    external_id = Column(Unicode, primary_key=True)
    coupons = relationship('Coupon', backref='group')
    customers = relationship('Customer', backref='group')
    plans = relationship('Plan', backref='group')
    payouts = relationship('Payout', backref='group')
    plan_invoices = relationship('PlanInvoice', backref='group')
    payout_invoices = relationship('PayoutInvoice', backref='group')

    @classmethod
    def create(cls, external_id):
        new_group = cls(external_id=external_id)
        cls.session.add(new_group)
        cls.session.commit()
        return new_group

    @classmethod
    def retrieve(cls, external_id):
        # Used one() instead get() to raise error if not found...
        return cls.query.filter(cls.external_id == external_id).one()
