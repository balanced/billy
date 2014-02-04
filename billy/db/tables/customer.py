from __future__ import unicode_literals

from sqlalchemy import Column
from sqlalchemy import Unicode
from sqlalchemy import Boolean
from sqlalchemy.schema import ForeignKey
from sqlalchemy.orm import relationship

from .base import DeclarativeBase
from .base import UTCDateTime
from .base import now_func


class Customer(DeclarativeBase):
    """A Customer is a target for charging or payout to

    """
    __tablename__ = 'customer'

    guid = Column(Unicode(64), primary_key=True)
    #: the guid of company which owns this customer
    company_guid = Column(
        Unicode(64),
        ForeignKey(
            'company.guid',
            ondelete='CASCADE', onupdate='CASCADE'
        ),
        index=True,
        nullable=False,
    )
    #: the URI of customer entity in payment processing system
    processor_uri = Column(Unicode(128), index=True)
    #: is this company deleted?
    deleted = Column(Boolean, default=False, nullable=False)
    #: the created datetime of this company
    created_at = Column(UTCDateTime, default=now_func)
    #: the updated datetime of this company
    updated_at = Column(UTCDateTime, default=now_func)

    #: subscriptions of this customer
    subscriptions = relationship('Subscription', cascade='all, delete-orphan',
                                 backref='customer')
    #: invoices of this customer
    invoices = relationship('CustomerInvoice', cascade='all, delete-orphan',
                            backref='customer')
__all__ = [
    Customer.__name__,
]
