from datetime import datetime

from sqlalchemy import Column, Unicode, ForeignKey, DateTime, Integer
from pytz import UTC

from billy.models.base import Base
from billy.utils.models import uuid_factory


class Transaction(Base):

    external_id = Column(Unicode, ForeignKey)
    group_id = Column(Unicode, ForeignKey('groups.guid'))
    customer_id = Column(Unicode, ForeignKey('customers.external_id'))
    created_at = Column(DateTime(timezone=UTC))
    amount_cents = Column(Integer)






class PaymentTransaction(Transaction):
    __tablename__ = 'payout_transactions'

    guid = Column(Unicode, primary_key=True, default=uuid_factory('PAT'))




class PayoutTransaction(Transaction):
    __tablename__ = 'payout_transactions'

    guid = Column(Unicode, primary_key=True, default=uuid_factory('POT'))