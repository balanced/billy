from __future__ import unicode_literals
from datetime import datetime

from sqlalchemy import Column, Unicode, ForeignKey, func, Boolean, Index
from sqlalchemy.orm import relationship

from models import Base
from utils.models import uuid_factory


class PayoutSubscription(Base):
    __tablename__ = 'payout_subscription'

    id = Column(Unicode, primary_key=True, default=uuid_factory('PS'))
    customer_id = Column(Unicode,
                         ForeignKey('customers.id', ondelete='cascade'),
                         nullable=False)
    payout_id = Column(Unicode,
                       ForeignKey('payout_plans.id', ondelete='cascade'),
                       nullable=False)
    is_active = Column(Boolean, default=True)

    customer = relationship('Customer')

    __table_args__ = (
        Index('unique_payout_sub', payout_id, customer_id,
              postgresql_where=is_active == True,
              unique=True),
    )

    @classmethod
    def create(cls, customer, payout):
        result = cls.query.filter(
            cls.customer == customer,
            cls.payout == payout).first()
        result = result or cls(
            customer=customer, payout=payout,
            # Todo Temp since default not working for some reason
            id=uuid_factory('PLL')())
        result.is_active = True
        cls.session.add(result)
        return result

    def generate_next_invoice(self):
        from models import PayoutPlan, PayoutPlanInvoice

        if not self.is_active:
            raise ValueError('Generating invoice for inactive plan!')
        invoice = self.invoices.filter(
            PayoutPlanInvoice.queue_rollover == True).first()
        if invoice:
            invoice.queue_rollover = False
            PayoutPlan.subscribe(self.customer,
                                 self.payout,
                                 first_now=False,
                                 start_dt=invoice.payout_date)

    @classmethod
    def generate_all_invoices(cls):
        from models import PayoutPlanInvoice

        needs_generation = cls.join(PayoutPlanInvoice).filter(
            PayoutPlanInvoice.queue_rollover == True,
            cls.is_active == True
        )

        needs_generation = PayoutPlanInvoice.query.join(cls).filter(
            PayoutPlanInvoice.queue_rollover == True,
            cls.is_active == True).all()
        for subscription in needs_generation:
            subscription.generate_next_invoice()


    @property
    def current_invoice(self):
        """
        Returns the current invoice of the customer. There can only be one
        invoice outstanding per customer PayoutPlan
        """
        from models import PayoutPlanInvoice

        return self.invoices.order_by(
            PayoutPlanInvoice.payout_date.desc()).first()

    def cancel(self, cancel_scheduled=False):
        from models import PayoutPlanInvoice

        self.is_active = False
        if cancel_scheduled:
            in_process = self.invoices.filter(
                PayoutPlanInvoice.completed == False).first()
            if in_process:
                in_process.completed = True
        return self
