from billy.models.base import Base
from sqlalchemy import Column, String, DateTime
from pytz import UTC
from datetime import datetime
from sqlalchemy.orm import mapper
from sqlalchemy import event
from utils import string_attr


class AuditEvents(Base):
    __tablename__ = 'auditevents'

    event_id = Column(String, primary_key=True)
    customer_id = Column(String)
    marketplace_id = Column(String)
    model_name = Column(String)
    plan_id = Column(String)
    payout_id = Column(String)
    coupon_id = Column(String)
    invoice_id = Column(String)
    event = Column(String)
    sql_event = Column(String)
    created_at = created_at = Column(DateTime(timezone=UTC),
                                     default=datetime.now(UTC))


    @staticmethod
    def process_listener(entity, event_type):
        new_audit = AuditEvents()
        new_audit.sql_event = event_type
        new_audit.coupon_id = string_attr(entity, 'coupon_id')
        new_audit.invoice_id = string_attr(entity, 'invoice_id')
        new_audit.model_name = entity.__name__
        new_audit.plan_id = string_attr(entity, 'plan_id')
        new_audit.marketplace_id = string_attr(entity, 'marketplace_id')
        new_audit.customer_id = string_attr(entity, 'customer_id')
        new_audit.payout_id = string_attr(entity, 'payout_id')
        new_audit.event = string_attr(entity, 'event')
        query_tool.add(new_audit)
        query_tool.commit()

    @staticmethod
    def insert_listener(mapper, connection, target):
        AuditEvents.process_listener(target, 'INSERT')

    @staticmethod
    def delete_listener(mapper, connection, target):
        AuditEvents.process_listener(target, 'DELETE')

    @staticmethod
    def update_listener(mapper, connection, target):
        AuditEvents.process_listener(target, 'UPDATE')


#initite listeners
event.listen(mapper, 'after_delete', AuditEvents.delete_listener)
event.listen(mapper, 'after_insert', AuditEvents.insert_listener)
event.listen(mapper, 'after_update', AuditEvents.update_listener)





