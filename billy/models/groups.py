from sqlalchemy import Unicode, Column
from sqlalchemy.orm import relationship

from base import Base
from billy.utils.models import uuid_factory
from billy.errors import AlreadyExistsError
from billy.models import *


class Group(Base):
    __tablename__ = 'groups'

    guid = Column(Unicode, primary_key=True, default=uuid_factory('CU'))
    external_id = Column(Unicode, unique=True)
    coupons = relationship('AuditEvent', backref='group')
    customers = relationship('Customer', backref='group')
    plan_invoices = relationship('PlanInvoice', backref='group')
    payout_invoices = relationship('PayoutInvoice', backref='group')




    @classmethod
    def create_group(cls, external_id):
        exists = cls.query.filter(cls.external_id == external_id)
        if exists:
            raise AlreadyExistsError('The group already exists in the db.')
        new_group = cls(external_id == external_id)
        cls.session.add(new_group)

    @classmethod
    def retrieve_group(cls, group_id):
        return cls.query.get(group_id)

