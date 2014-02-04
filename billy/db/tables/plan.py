from __future__ import unicode_literals

from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import Unicode
from sqlalchemy import UnicodeText
from sqlalchemy import Boolean
from sqlalchemy.schema import ForeignKey
from sqlalchemy.orm import relationship

from .base import DeclarativeBase
from .base import UTCDateTime
from .base import now_func
from ..enum import DeclEnum


class PlanType(DeclEnum):

    DEBIT = 'DEBIT', 'Debit'
    CREDIT = 'CREDIT', 'Credit'


class PlanFrequency(DeclEnum):

    DAILY = 'DAILY', 'Daily'
    WEEKLY = 'WEEKLY', 'Weekly'
    MONTHLY = 'MONTHLY', 'Monthly'
    YEARLY = 'YEARLY', 'Yearly'


class Plan(DeclarativeBase):
    """Plan is a recurring payment schedule, such as a hosting service plan.

    """
    __tablename__ = 'plan'

    guid = Column(Unicode(64), primary_key=True)
    #: the guid of company which owns this plan
    company_guid = Column(
        Unicode(64),
        ForeignKey(
            'company.guid',
            ondelete='CASCADE', onupdate='CASCADE'
        ),
        index=True,
        nullable=False,
    )
    #: what kind of plan it is, could be DEBIT or CREDIT
    plan_type = Column(PlanType.db_type(), nullable=False, index=True)
    #: the external ID given by user
    external_id = Column(Unicode(128), index=True)
    #: a short name of this plan
    name = Column(Unicode(128))
    #: a long description of this plan
    description = Column(UnicodeText)
    #: the amount to bill user
    # TODO: make sure how many digi of number we need
    # TODO: Fix SQLite doesn't support decimal issue?
    amount = Column(Integer, nullable=False)
    #: the fequency to bill user, could be DAILY, WEEKLY, MONTHLY, YEARLY
    frequency = Column(PlanFrequency.db_type(), nullable=False)
    #: interval of period, for example, interval 3 with weekly frequency
    #  means this plan will do transaction every 3 weeks
    interval = Column(Integer, nullable=False, default=1)
    #: is this plan deleted?
    deleted = Column(Boolean, default=False, nullable=False)
    #: the created datetime of this plan
    created_at = Column(UTCDateTime, default=now_func)
    #: the updated datetime of this plan
    updated_at = Column(UTCDateTime, default=now_func)

    #: subscriptions of this plan
    subscriptions = relationship('Subscription', cascade='all, delete-orphan',
                                 backref='plan')

__all__ = [
    PlanType.__name__,
    PlanFrequency.__name__,
    Plan.__name__,
]
