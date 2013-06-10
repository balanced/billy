from datetime import datetime

from sqlalchemy import Column, Unicode, ForeignKey, DateTime, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.schema import ForeignKeyConstraint
from pytz import UTC

from billy.models.base import Base
from billy.models.invoices import PlanInvoice, PayoutInvoice
from billy.models.customers import Customer
from billy.utils.models import uuid_factory, Status
from billy.settings import TRANSACTION_PROVIDER_CLASS


class Transaction(Base):
    external_id = Column(Unicode, ForeignKey)
    group_id = Column(Unicode)
    customer_id = Column(Unicode)
    created_at = Column(DateTime(timezone=UTC))
    amount_cents = Column(Integer)
    status = Column(Unicode)

    __table_args__ = (
        #Customer foreign key
        ForeignKeyConstraint(
            [customer_id, group_id],
            [Customer.external_id, Customer.group_id]),
    )

    charge_callable = NotImplementedError

    @classmethod
    def create(cls, customer_id, group_id, amount_cents):
        new_transaction = cls(
            group_id=group_id,
            customer_id=customer_id,
            amount_cents=amount_cents,
            status = Status.PENDING
        )
        cls.session.add(new_transaction)
        cls.session.commit()
        return cls

    def execute(self):
        try:
            self.charge_callable(self.customer_id, self.group_id, self.amount_cents)
            self.status = Status.COMPLETE
        except Exception, e:
            self.status = Status.ERROR
            raise e
        self.session.commit()

    @classmethod
    def retrieve(cls, group_id, customer_id=None, external_id=None):
        query = cls.query.filter(cls.group_id == group_id)
        if customer_id:
            query.filter(cls.customer_id == customer_id)
        if external_id:
            query.filter(cls.external_id == external_id)
        return query.all()


    #Todo retry ERROR status ones.


class PaymentTransaction(Transaction):
    __tablename__ = 'payment_transactions'

    charge_callable = TRANSACTION_PROVIDER_CLASS.make_payout

    guid = Column(Unicode, primary_key=True, default=uuid_factory('PAT'))
    plan_invoices = relationship(PlanInvoice.__name__, backref='transaction')


class PayoutTransaction(Transaction):
    __tablename__ = 'payout_transactions'

    charge_callable = TRANSACTION_PROVIDER_CLASS.create_charge

    guid = Column(Unicode, primary_key=True, default=uuid_factory('POT'))
    payout_invoices = relationship(PayoutInvoice.__name__,
                                 backref='transaction')