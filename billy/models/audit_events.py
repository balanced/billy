from pytz import UTC
from datetime import datetime
from sqlalchemy.orm import mapper
from sqlalchemy import event, ForeignKey
from sqlalchemy import Column, Unicode, DateTime

from billy.models.base import Base
from billy.models.groups import Group
from billy.utils.audit_events import string_attr
from billy.utils.models import uuid_factory


class AuditEvent(Base):
    __tablename__ = 'audit_events'

    guid = Column(Unicode, primary_key=True, default=uuid_factory('CU'))
    obj_guid = Column(Unicode)
    customer_id = Column(Unicode)
    external_id = Column(Unicode)
    group_id = Column(Unicode, ForeignKey(Group.external_id))
    model_name = Column(Unicode)
    plan_id = Column(Unicode)
    payout_id = Column(Unicode)
    coupon_id = Column(Unicode)
    invoice_id = Column(Unicode)
    event = Column(Unicode)
    sql_event = Column(Unicode)
    created_at = created_at = Column(DateTime(timezone=UTC),
                                     default=datetime.now(UTC))


    @classmethod
    def create_from_event(cls, entity, event_type):
        new_audit = cls()
        new_audit.sql_event = event_type
        new_audit.coupon_id = string_attr(entity, 'coupon_id')
        new_audit.invoice_id = string_attr(entity, 'invoice_id')
        new_audit.model_name = entity.__name__
        new_audit.obj_guid = string_attr(entity, 'guid')
        new_audit.plan_id = string_attr(entity, 'plan_id')
        new_audit.group_id = string_attr(entity, 'group_id')
        new_audit.customer_id = string_attr(entity, 'customer_id')
        new_audit.payout_id = string_attr(entity, 'payout_id')
        new_audit.external_id = string_attr(entity, 'external_id')
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





