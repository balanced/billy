from billy.models.base import Base
from sqlalchemy import Column, String, DateTime
from pytz import UTC
from datetime import datetime
from sqlalchemy.schema import ForeignKey



class AuditEvents(Base):
    __tablename__ = 'auditevents'

    event_id = Column(String, primary_key=True)
    customer_id = Column(String, ForeignKey('customers.customer_id'))
    marketplace_id = Column(String)
    plan_id = Column(String, ForeignKey('plans.plan_id'))
    coupon_id = Column(String, ForeignKey('coupons.coupon_id'))
    invoice_id = Column(String, ForeignKey('invoices.invoice_id'))
    event = Column(String)
    created_at = created_at = Column(DateTime(timezone=UTC), default=datetime.now(UTC))



