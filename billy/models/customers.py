from __future__ import unicode_literals
from datetime import datetime

from sqlalchemy import Column, Unicode, DateTime, Integer
from sqlalchemy.schema import ForeignKey, UniqueConstraint
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import relationship

from billy.models import Base, ChargeSubscription, PayoutSubscription
from billy.utils.models import uuid_factory


class Customer(Base):
    __tablename__ = 'customers'

    id = Column(Unicode, primary_key=True, default=uuid_factory('CU'))
    company_id = Column(Unicode, ForeignKey('companies.id', ondelete='cascade'),
                        nullable=False)
    your_id = Column(Unicode, nullable=False)
    processor_id = Column(Unicode, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow)

    charge_subscriptions = relationship('ChargeSubscription',
                                       cascade='delete', lazy='dynamic')
    charge_invoices = association_proxy('charge_subscriptions', 'invoices')

    charge_transactions = relationship('ChargeTransaction',
                                       backref='customer', cascade='delete',
                                       lazy='dynamic')

    payout_subscriptions = relationship('PayoutSubscription',
                                        backref='customer',
                                        cascade='delete', lazy='dynamic')
    payout_invoices = association_proxy('payout_subscriptions', 'invoices')

    payout_transactions = relationship('PayoutTransaction',
                                       backref='customer', cascade='delete',
                                       lazy='dynamic')

    __table_args__ = (
        UniqueConstraint(
            your_id, company_id, name='yourid_company_unique'),
    )


    @property
    def charge_subscriptions(self):
        return ChargeSubscription.query.filter(
            ChargeSubscription.customer == self,
            ChargeSubscription.is_enrolled == True).all()


    @property
    def payout_subscriptions(self):
        return PayoutSubscription.query.filter(
            PayoutSubscription.customer == self,
            ChargeSubscription.is_active == True).all()



