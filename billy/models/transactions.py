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

    @classmethod
    def create(cls, external_id, group_id, customer_id, amount_cents):
        new_transaciton = cls(
            external_id=external_id,
            group_id=group_id,
            customer_id=customer_id,
            amount_cents=amount_cents,
        )
        cls.session.add(new_transaciton)
        cls.session.commit()


    @classmethod
    def retrieve(cls, group_id, customer_id=None, external_id=None):
        query = cls.query.filter(cls.group_id == group_id)
        if customer_id:
            query.filter(cls.customer_id == customer_id)
        if external_id:
            query.filter(cls.external_id == external_id)
        return query.all()


class PaymentTransaction(Transaction):
    __tablename__ = 'payout_transactions'

    guid = Column(Unicode, primary_key=True, default=uuid_factory('PAT'))


class PayoutTransaction(Transaction):
    __tablename__ = 'payout_transactions'

    guid = Column(Unicode, primary_key=True, default=uuid_factory('POT'))