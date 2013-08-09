from datetime import datetime

from sqlalchemy import (Column, Unicode, ForeignKey, DateTime, Boolean,
                        Integer, CheckConstraint)
from sqlalchemy.orm import relationship, backref

from models import Base, PayoutSubscription
import settings
from utils.models import uuid_factory


class PayoutPlanInvoice(Base):
    __tablename__ = 'payout_plan_invoices'

    id = Column(Unicode, primary_key=True, default=uuid_factory('POI'))
    subscription_id = Column(Unicode, ForeignKey('payout_subscription.id',
                                                 ondelete='cascade'),
                             nullable=False)
    payout_date = Column(DateTime)
    balance_to_keep_cents = Column(Integer, CheckConstraint(
        'balance_to_keep_cents >= 0'))
    amount_payed_out = Column(Integer, nullable=False, default=0)
    completed = Column(Boolean, default=False)
    queue_rollover = Column(Boolean, default=False)
    balance_at_exec = Column(Integer,
                             nullable=True)
    attempts_made = Column(Integer, CheckConstraint('attempts_made >= 0'),
                           default=0)

    transaction = relationship('PayoutTransaction', backref='invoice',
                               cascade='delete', uselist=False)

    subscription = relationship('PayoutSubscription',
                                backref=backref('invoices', lazy='dynamic',
                                                cascade='delete'),
    )

    @classmethod
    def create(cls, subscription,
               payout_date, balanced_to_keep_cents):
        invoice = cls(
            subscription=subscription,
            payout_date=payout_date,
            balance_to_keep_cents=balanced_to_keep_cents,
        )
        cls.session.add(invoice)
        return invoice

    @classmethod
    def settle_all(cls):
        now = datetime.utcnow()
        needs_settling = cls.query.filter(cls.payout_date <= now,
                                          cls.completed == False).all()
        for invoice in needs_settling:
            if len(settings.RETRY_DELAY_PAYOUT) < invoice.attempts_made:
                invoice.subscription.is_active = False
            else:
                retry_delay = sum(
                    settings.RETRY_DELAY_PAYOUT[:invoice.attempts_made])
                when_to_payout = invoice.payout_date + retry_delay if \
                    retry_delay else invoice.payout_date
                if when_to_payout <= now:
                    invoice.settle()
        return len(needs_settling)

    def settle(self):
        from models import PayoutTransaction

        transactor = self.subscription.customer.company.processor
        current_balance = transactor.check_balance(
            self.subscription.customer.processor_id)
        payout_amount = current_balance - self.balance_to_keep_cents
        transaction = PayoutTransaction.create(
            self.subscription.customer, payout_amount)
        transaction.invoice_id = self.id
        try:
            self.balance_at_exec = current_balance
            self.amount_payed_out = payout_amount
            self.completed = True
            self.queue_rollover = True
        except Exception, e:
            self.attempts_made += 1
            self.session.commit()
            raise e
        return self

