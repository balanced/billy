from sqlalchemy import Unicode, Column
from sqlalchemy.orm import relationship

from base import Base
from billy.errors import AlreadyExistsError
from models import *


class Group(Base):
    __tablename__ = 'groups'

    guid = Column(Unicode, primary_key=True)
    coupons = relationship(AuditEvent.__name__, backref='group')
    customers = relationship(Customer.__name__, backref='group')
    plan_invoices = relationship(PlanInvoice.__name__, backref='group')
    payout_invoices = relationship(PayoutInvoice.__name__, backref='group')




    @classmethod
    def create_group(cls, group_id):
        exists = cls.query.get(group_id)
        if exists:
            raise AlreadyExistsError('The group already exists in the db.')
        new_group = cls(uid = group_id)
        cls.session.add(new_group)

    @classmethod
    def retrieve_group(cls, group_id):
        return cls.query.get(group_id)

