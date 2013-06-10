from pytz import UTC
from datetime import datetime
from sqlalchemy.orm import mapper
from sqlalchemy import event, ForeignKey
from sqlalchemy import Column, String, DateTime, Unicode

from billy.models.base import Base
from billy.models.groups import Group
from billy.utils.audit_events import string_attr
from billy.utils.models import uuid_factory


class AuditEvent(Base):
    __tablename__ = 'audit_events'

    guid = Column(Unicode, primary_key=True, default=uuid_factory('CU'))
    customer_id = Column(String)
    group_id = Column(String, ForeignKey(Group.external_id))
    model_name = Column(String)
    plan_id = Column(String)
    payout_id = Column(String)
    coupon_id = Column(String)
    invoice_id = Column(String)
    event = Column(String)
    sql_event = Column(String)
    created_at = created_at = Column(DateTime(timezone=UTC),
                                     default=datetime.now(UTC))


    @classmethod
    def create_from_event(cls, entity, event_type):
        new_audit = cls()
        new_audit.sql_event = event_type
        new_audit.coupon_id = string_attr(entity, 'coupon_id')
        new_audit.invoice_id = string_attr(entity, 'invoice_id')
        new_audit.model_name = entity.__name__
        new_audit.plan_id = string_attr(entity, 'plan_id')
        new_audit.group_id = string_attr(entity, 'group_id')
        new_audit.customer_id = string_attr(entity, 'customer_id')
        new_audit.payout_id = string_attr(entity, 'payout_id')
        #Todo add events everwhere...
        new_audit.event = string_attr(entity, 'event')
        cls.session.add(new_audit)
        cls.session.commit()

    @staticmethod
    def insert_listener(mapper, connection, target):
        AuditEvent.create_from_event(target, 'INSERT')

    @staticmethod
    def delete_listener(mapper, connection, target):
        AuditEvent.create_from_event(target, 'DELETE')

    @staticmethod
    def update_listener(mapper, connection, target):
        AuditEvent.create_from_event(target, 'UPDATE')


#initite listeners
event.listen(mapper, 'after_delete', AuditEvent.delete_listener)
event.listen(mapper, 'after_insert', AuditEvent.insert_listener)
event.listen(mapper, 'after_update', AuditEvent.update_listener)





