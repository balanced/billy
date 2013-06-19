from __future__ import unicode_literals

from datetime import datetime
from pytz import UTC
from sqlalchemy.orm import mapper
from sqlalchemy import event
from sqlalchemy import Column, Unicode, DateTime

from billy.models import *
from billy.utils.billy_action import string_attr
from billy.utils.models import uuid_factory


class BillyAction(Base):

    """
    This is a simple transaction logger that should be seldom queried.
    WORK IN PROGRESS.
    Note: No FKeys here because it'd be wasted index. Its a catch all so relational
    querying might not make too much sense...
    """
    __tablename__ = 'billy_actions'

    guid = Column(Unicode, primary_key=True, default=uuid_factory('CU'))
    obj_guid = Column(Unicode)
    customer_id = Column(Unicode)
    external_id = Column(Unicode)
    group_id = Column(Unicode)
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
        new_audit.model_name = getattr(entity, '__tablename__', None)
        new_audit.obj_guid = string_attr(entity, 'guid')
        new_audit.plan_id = string_attr(entity, 'plan_id')
        new_audit.group_id = string_attr(entity, 'group_id')
        new_audit.customer_id = string_attr(entity, 'customer_id')
        new_audit.payout_id = string_attr(entity, 'payout_id')
        new_audit.external_id = string_attr(entity, 'external_id')
        new_audit.event = string_attr(entity, 'event')
        # cls.session.add(new_audit)
        # cls.session.commit() Todo check this out...

    @staticmethod
    def insert_listener(mapper, connection, target):
        BillyAction.create_from_event(target, 'INSERT')

    @staticmethod
    def delete_listener(mapper, connection, target):
        BillyAction.create_from_event(target, 'DELETE')

    @staticmethod
    def update_listener(mapper, connection, target):
        BillyAction.create_from_event(target, 'UPDATE')


# initiate listeners
event.listen(mapper, 'after_delete', BillyAction.delete_listener)
event.listen(mapper, 'after_insert', BillyAction.insert_listener)
event.listen(mapper, 'after_update', BillyAction.update_listener)
