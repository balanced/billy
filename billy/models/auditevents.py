from billy.models.base import Base
from sqlalchemy import Column, String, DateTime
from pytz import UTC
from datetime import datetime
from sqlalchemy.orm import mapper
from sqlalchemy import event
from utils.auditevents import string_attr


class AuditEvent(Base):
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


    @classmethod
    def process_listener(cls, entity, event_type):
        new_audit = cls()
        new_audit.sql_event = event_type
        new_audit.coupon_id = string_attr(entity, 'coupon_id')
        new_audit.invoice_id = string_attr(entity, 'invoice_id')
        new_audit.model_name = entity.__name__
        new_audit.plan_id = string_attr(entity, 'plan_id')
        new_audit.marketplace_id = string_attr(entity, 'marketplace_id')
        new_audit.customer_id = string_attr(entity, 'customer_id')
        new_audit.payout_id = string_attr(entity, 'payout_id')
        #Todo add events everwhere...
        new_audit.event = string_attr(entity, 'event')
        cls.session.add(new_audit)
        cls.session.commit()

    @staticmethod
    def insert_listener(mapper, connection, target):
        AuditEvent.process_listener(target, 'INSERT')

    @staticmethod
    def delete_listener(mapper, connection, target):
        AuditEvent.process_listener(target, 'DELETE')

    @staticmethod
    def update_listener(mapper, connection, target):
        AuditEvent.process_listener(target, 'UPDATE')


#initite listeners
event.listen(mapper, 'after_delete', AuditEvent.delete_listener)
event.listen(mapper, 'after_insert', AuditEvent.insert_listener)
event.listen(mapper, 'after_update', AuditEvent.update_listener)





