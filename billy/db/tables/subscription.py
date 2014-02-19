from __future__ import unicode_literals

from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import Unicode
from sqlalchemy import Boolean
from sqlalchemy.schema import ForeignKey
from sqlalchemy.orm import relationship

from .base import DeclarativeBase
from .base import UTCDateTime
from .base import now_func


class Subscription(DeclarativeBase):
    """A subscription relationship between Customer and Plan

    """
    __tablename__ = 'subscription'

    guid = Column(Unicode(64), primary_key=True)
    #: the guid of customer who subscribes
    customer_guid = Column(
        Unicode(64),
        ForeignKey(
            'customer.guid',
            ondelete='CASCADE', onupdate='CASCADE'
        ),
        index=True,
        nullable=False,
    )
    #: the guid of plan customer subscribes to
    plan_guid = Column(
        Unicode(64),
        ForeignKey(
            'plan.guid',
            ondelete='CASCADE', onupdate='CASCADE'
        ),
        index=True,
        nullable=False,
    )
    #: the funding instrument URI to charge/payout, such as bank account or
    #  credit card
    funding_instrument_uri = Column(Unicode(128), index=True)
    #: if this amount is not null, the amount of plan will be overwritten
    amount = Column(Integer)
    #: the external ID given by user
    external_id = Column(Unicode(128), index=True)
    #: the statement to appear on customer's transaction record (either
    #  bank account or credit card)
    appears_on_statement_as = Column(Unicode(32))
    #: is this subscription canceled?
    canceled = Column(Boolean, default=False, nullable=False)
    #: the next datetime to charge or pay out
    next_invoice_at = Column(UTCDateTime, nullable=False)
    #: the started datetime of this subscription
    started_at = Column(UTCDateTime, nullable=False)
    #: the canceled datetime of this subscription
    canceled_at = Column(UTCDateTime, default=None)
    #: the created datetime of this subscription
    created_at = Column(UTCDateTime, default=now_func)
    #: the updated datetime of this subscription
    updated_at = Column(UTCDateTime, default=now_func)

    #: invoices of this subscription
    invoices = relationship(
        'SubscriptionInvoice',
        cascade='all, delete-orphan',
        backref='subscription',
        lazy='dynamic',
        order_by='SubscriptionInvoice.scheduled_at.desc()'
    )

    @property
    def effective_amount(self):
        """The effective amount of this subscription, if the amount is None
        on this subscription, plan's amount will be returned

        """
        if self.amount is None:
            return self.plan.amount
        return self.amount

    @property
    def invoice_count(self):
        """How many invoice has been generated

        """
        return self.invoices.count()

__all__ = [
    Subscription.__name__,
]
