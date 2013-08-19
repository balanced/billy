from __future__ import unicode_literals

from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import Unicode
from sqlalchemy import UnicodeText
from sqlalchemy import Boolean
from sqlalchemy import DateTime
from sqlalchemy import Numeric
from sqlalchemy.schema import ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.orm import backref
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql.expression import func

DeclarativeBase = declarative_base()

#: The now function for database relative operation
_now_func = [func.utc_timestamp]


def set_now_func(func):
    """Replace now function and return the old function
    
    """
    old = _now_func[0]
    _now_func[0] = func
    return old


def get_now_func():
    """Return current now func
    
    """
    return _now_func[0]


def now_func():
    """Return current datetime
    
    """
    func = _now_func[0]
    return func()


class Company(DeclarativeBase):
    """A Company is basically a user to billy system

    """
    __tablename__ = 'company'

    guid = Column(Unicode(64), primary_key=True)
    #: the API key for accessing billy system
    api_key = Column(Unicode(64), unique=True, index=True, nullable=False)
    #: the processor key (it would be balanced API key if we are using balanced)
    processor_key = Column(Unicode(64), index=True, nullable=False)
    #: a short optional name of this company
    name = Column(Unicode(128))
    #: is this company deleted?
    deleted = Column(Boolean, default=False, nullable=False)
    #: the created datetime of this company
    created_at = Column(DateTime(timezone=True), default=now_func)
    #: the updated datetime of this company
    updated_at = Column(DateTime(timezone=True), default=now_func)

    #: plans of this company
    plans = relationship('Plan', cascade='all, delete-orphan', backref='company')
    #: customers of this company
    customers = relationship('Customer', cascade='all, delete-orphan', backref='company')


class Customer(DeclarativeBase):
    """A Customer is basically a user to billy system

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
    #: the external ID given by user
    external_id = Column(Unicode(128), index=True)
    #: the payment URI associated with this customer
    payment_uri = Column(Unicode(128), index=True, nullable=False)
    #: a short optional name of this company
    name = Column(Unicode(128))
    #: is this company deleted?
    deleted = Column(Boolean, default=False, nullable=False)
    #: the created datetime of this company
    created_at = Column(DateTime(timezone=True), default=now_func)
    #: the updated datetime of this company
    updated_at = Column(DateTime(timezone=True), default=now_func)

    #: subscriptions of this customer
    subscriptions = relationship('Subscription', cascade='all, delete-orphan', backref='customer')


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
    #: what kind of plan it is, 0=charge, 1=payout
    plan_type = Column(Integer, nullable=False, index=True)
    #: the external ID given by user
    external_id = Column(Unicode(128), index=True)
    #: a short name of this plan
    name = Column(Unicode(128))
    #: a long description of this plan
    description = Column(UnicodeText(1024))
    #: the amount to bill user
    # TODO: make sure how many digi of number we need
    # TODO: Fix SQLite doesn't support decimal issue?
    amount = Column(Numeric(10, 2), nullable=False)
    #: the fequency to bill user, 0=daily, 1=weekly, 2=monthly
    frequency = Column(Integer, nullable=False)
    #: interval of period, for example, interval 3 with weekly frequency
    #  means this plan will do transaction every 3 weeks
    interval = Column(Integer, nullable=False, default=1)
    #: is this plan deleted?
    deleted = Column(Boolean, default=False, nullable=False)
    #: the created datetime of this plan
    created_at = Column(DateTime(timezone=True), default=now_func)
    #: the updated datetime of this plan
    updated_at = Column(DateTime(timezone=True), default=now_func)

    #: subscriptions of this plan
    subscriptions = relationship('Subscription', cascade='all, delete-orphan', backref='plan')


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
    #: the discount of this subscription, 
    #  e.g. 0.3 means 30% price off disscount
    discount = Column(Numeric(10, 2))
    #: the external ID given by user
    external_id = Column(Unicode(128), index=True)
    #: is this subscription canceled?
    canceled = Column(Boolean, default=False, nullable=False)
    #: the next datetime to charge or pay out
    next_transaction_at = Column(DateTime(timezone=True), nullable=False)
    #: how many transaction has been generated
    period = Column(Integer, nullable=False, default=0)
    #: the started datetime of this subscription
    started_at = Column(DateTime(timezone=True), nullable=False)
    #: the canceled datetime of this subscription 
    canceled_at = Column(DateTime(timezone=True), default=None)
    #: the created datetime of this subscription 
    created_at = Column(DateTime(timezone=True), default=now_func)
    #: the updated datetime of this subscription 
    updated_at = Column(DateTime(timezone=True), default=now_func)

    #: transactions of this subscription
    transactions = relationship('Transaction', cascade='all, delete-orphan', 
                                backref='subscription')


class Transaction(DeclarativeBase):
    """A transaction of subscription, typically, this can be a bank charging
    or credit card debiting operation. It could also be a refunding or paying
    out operation.

    """
    __tablename__ = 'transaction'

    guid = Column(Unicode(64), primary_key=True)
    #: the guid of subscription which generated this transaction
    subscription_guid = Column(
        Unicode(64), 
        ForeignKey(
            'subscription.guid', 
            ondelete='CASCADE', onupdate='CASCADE'
        ), 
        index=True,
        nullable=False,
    )
    #: the guid of target transaction to refund to
    refund_to_guid = Column(
        Unicode(64), 
        ForeignKey(
            'transaction.guid', 
            ondelete='CASCADE', onupdate='CASCADE'
        ), 
        index=True,
    )
    #: what type of transaction it is, 0=charge, 1=refund, 2=payout
    transaction_type = Column(Integer, index=True, nullable=False)
    #: current status of this transaction, could be
    #  0=init, 1=retrying, 2=done, 3=failed
    # TODO: what about retry?
    status = Column(Integer, index=True, nullable=False)
    #: the amount to do transaction (charge, payout or refund)
    amount = Column(Numeric(10, 2), index=True, nullable=False)
    #: the payment URI
    payment_uri = Column(Unicode(128), index=True)
    #: the scheduled datetime of this transaction should be processed
    scheduled_at = Column(DateTime(timezone=True), default=now_func)
    #: the created datetime of this subscription 
    created_at = Column(DateTime(timezone=True), default=now_func)
    #: the updated datetime of this subscription 
    updated_at = Column(DateTime(timezone=True), default=now_func)

    #: target transaction of refund transaction
    refund_to = relationship(
        'Transaction', 
        cascade='all, delete-orphan', 
        backref=backref('refund_from', uselist=False), 
        remote_side=[guid], 
        uselist=False, 
        single_parent=True,
    )
