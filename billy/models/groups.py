from sqlalchemy import Unicode, Column
from sqlalchemy.orm import relationship

from base import Base
from billy.utils.models import uuid_factory
from billy.errors import AlreadyExistsError
from models import *


class Group(Base):
    __tablename__ = 'groups'

    guid = Column(Unicode, primary_key=True, default=uuid_factory('CU'))
    external_id = Column(Unicode, unique=True)
    coupons = relationship(AuditEvent.__name__, backref='group')
    customers = relationship(Customer.__name__, backref='group')
    plan_invoices = relationship(PlanInvoice.__name__, backref='group')
    payout_invoices = relationship(PayoutInvoice.__name__, backref='group')




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

