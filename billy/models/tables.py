from __future__ import unicode_literals

from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import Unicode
from sqlalchemy import UnicodeText
from sqlalchemy import Boolean
from sqlalchemy import DateTime
from sqlalchemy.schema import ForeignKey
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.orm import backref
from sqlalchemy.orm import object_session
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
    func = get_now_func()
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
    created_at = Column(DateTime, default=now_func)
    #: the updated datetime of this company
    updated_at = Column(DateTime, default=now_func)

    #: plans of this company
    plans = relationship('Plan', cascade='all, delete-orphan', 
                         backref='company')
    #: customers of this company
    customers = relationship('Customer', cascade='all, delete-orphan', 
                             backref='company')


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
    created_at = Column(DateTime, default=now_func)
    #: the updated datetime of this company
    updated_at = Column(DateTime, default=now_func)

    #: subscriptions of this customer
    subscriptions = relationship('Subscription', cascade='all, delete-orphan', 
                                 backref='customer')
    #: invoices of this customer
    invoices = relationship('CustomerInvoice', cascade='all, delete-orphan', 
                            backref='customer')


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
    description = Column(UnicodeText)
    #: the amount to bill user
    # TODO: make sure how many digi of number we need
    # TODO: Fix SQLite doesn't support decimal issue?
    amount = Column(Integer, nullable=False)
    #: the fequency to bill user, 0=daily, 1=weekly, 2=monthly
    frequency = Column(Integer, nullable=False)
    #: interval of period, for example, interval 3 with weekly frequency
    #  means this plan will do transaction every 3 weeks
    interval = Column(Integer, nullable=False, default=1)
    #: is this plan deleted?
    deleted = Column(Boolean, default=False, nullable=False)
    #: the created datetime of this plan
    created_at = Column(DateTime, default=now_func)
    #: the updated datetime of this plan
    updated_at = Column(DateTime, default=now_func)

    #: subscriptions of this plan
    subscriptions = relationship('Subscription', cascade='all, delete-orphan', 
                                 backref='plan')


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
    next_invoice_at = Column(DateTime, nullable=False)
    #: the started datetime of this subscription
    started_at = Column(DateTime, nullable=False)
    #: the canceled datetime of this subscription 
    canceled_at = Column(DateTime, default=None)
    #: the created datetime of this subscription 
    created_at = Column(DateTime, default=now_func)
    #: the updated datetime of this subscription 
    updated_at = Column(DateTime, default=now_func)

    #: invoices of this subscription
    invoices = relationship(
        'SubscriptionInvoice', 
        cascade='all, delete-orphan', 
        backref='subscription',
        lazy='dynamic',
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


class Invoice(DeclarativeBase):
    """An invoice

    """
    __tablename__ = 'invoice'
    __mapper_args__ = {
        'polymorphic_on': 'invoice_type',
    } 

    guid = Column(Unicode(64), primary_key=True)
    # type of invoice, could be 0=subscription, 1=customer
    invoice_type = Column(Integer, index=True, nullable=False)
    #: what kind of transaction it is, 0=charge, 2=payout
    transaction_type = Column(Integer, nullable=False, index=True)
    #: the funding instrument URI to charge to, such as bank account or credit 
    #  card
    funding_instrument_uri = Column(Unicode(128), index=True)
    #: the total amount of this invoice
    amount = Column(Integer, nullable=False)
    #: current status of this invoice, could be
    #   - 0=init 
    #   - 1=processing
    #   - 2=settled
    #   - 3=canceled
    #   - 4=process failed
    #   - 5=refunding
    #   - 6=refunded
    #   - 7=refund failed
    status = Column(Integer, index=True, nullable=False)
    #: a short optional title of this invoice
    title = Column(Unicode(128))
    #: the created datetime of this invoice 
    created_at = Column(DateTime, default=now_func)
    #: the updated datetime of this invoice 
    updated_at = Column(DateTime, default=now_func)
    #: the statement to appear on customer's transaction record (either 
    #  bank account or credit card)
    appears_on_statement_as = Column(Unicode(32))

    #: the last transaction of this invoice
    last_transaction = relationship(
        'Transaction', 
        uselist=False,
        order_by='-Transaction.created_at',
    )

    #: transactions of this invoice
    transactions = relationship(
        'Transaction', 
        cascade='all, delete-orphan', 
        backref='invoice'
    )

    #: items of this invoice
    items = relationship(
        'Item', 
        cascade='all, delete-orphan', 
        backref='invoice',
        order_by='Item.item_id',
    )

    #: adjustments of this invoice
    adjustments = relationship(
        'Adjustment', 
        cascade='all, delete-orphan', 
        backref='invoice',
        order_by='Adjustment.adjustment_id',
    )

    @property
    def total_adjustment_amount(self):
        """Sum of total adjustment amount

        """
        from sqlalchemy import func
        session = object_session(self)
        return (
            session.query(func.coalesce(func.sum(Adjustment.total), 0))
            .filter(Adjustment.invoice_guid == self.guid)
            .scalar()
        )

    @property
    def effective_amount(self):
        """Effect amount of this invoice (amount + total_adjustment_amount)

        """
        return self.total_adjustment_amount + self.amount


class SubscriptionInvoice(Invoice):
    """An invoice generated from subscription (recurring charge or payout)

    """
    __tablename__ = 'subscription_invoice'
    __mapper_args__ = {
        'polymorphic_identity': 0,
    } 

    guid = Column(
        Unicode(64), 
        ForeignKey(
            'invoice.guid', 
            ondelete='CASCADE', 
            onupdate='CASCADE'
        ), 
        primary_key=True,
    )
    #: the guid of subscription which generated this invoice
    subscription_guid = Column(
        Unicode(64), 
        ForeignKey(
            'subscription.guid', 
            ondelete='CASCADE', onupdate='CASCADE'
        ), 
        index=True,
        nullable=False,
    )
    #: the scheduled datetime of this invoice should be processed
    scheduled_at = Column(DateTime, default=now_func)

    @property
    def customer(self):
        return self.subscription.customer


class CustomerInvoice(Invoice):
    """A single invoice generated for customer

    """
    __tablename__ = 'customer_invoice'
    __table_args__ = (UniqueConstraint('customer_guid', 'external_id'), )
    __mapper_args__ = {
        'polymorphic_identity': 1,
    } 

    guid = Column(
        Unicode(64), 
        ForeignKey(
            'invoice.guid', 
            ondelete='CASCADE', 
            onupdate='CASCADE'
        ), 
        primary_key=True,
    )
    #: the guid of customer who owns this invoice
    customer_guid = Column(
        Unicode(64), 
        ForeignKey(
            'customer.guid', 
            ondelete='CASCADE', onupdate='CASCADE'
        ), 
        index=True,
        nullable=False,
    )
    #: the external_id for storing external resource ID in order to avoid 
    #  duplication
    external_id = Column(Unicode(128), index=True)


class Item(DeclarativeBase):
    """An item of an invoice

    """
    __tablename__ = 'item'

    item_id = Column(Integer, autoincrement=True, primary_key=True)
    #: the guid of invoice which owns this item
    invoice_guid = Column(
        Unicode(64), 
        ForeignKey(
            'invoice.guid', 
            ondelete='CASCADE', onupdate='CASCADE'
        ), 
        index=True,
        nullable=False,
    )
    #: type of this item
    type = Column(Unicode(128))
    #: name of item
    name = Column(Unicode(128), nullable=False)
    #: quantity of item
    quantity = Column(Integer)
    #: total processed transaction amount
    amount = Column(Integer)
    #: total fee to charge for this item
    total = Column(Integer, nullable=False)
    #: unit of item
    unit = Column(Unicode(64))


class Adjustment(DeclarativeBase):
    """An adjustment to invoice

    """
    __tablename__ = 'adjustment'

    adjustment_id = Column(Integer, autoincrement=True, primary_key=True)
    #: the guid of invoice which owns this adjustment
    invoice_guid = Column(
        Unicode(64), 
        ForeignKey(
            'invoice.guid', 
            ondelete='CASCADE', onupdate='CASCADE'
        ), 
        index=True,
        nullable=False,
    )
    #: reason of making this adjustment to invoice
    reason = Column(Unicode(128))
    #: total adjustment applied to the invoice, could be negative
    total = Column(Integer, nullable=False)


class Transaction(DeclarativeBase):
    """A transaction 

    """
    __tablename__ = 'transaction'

    guid = Column(Unicode(64), primary_key=True)
    #: the guid of invoice which owns this transaction
    invoice_guid = Column(
        Unicode(64), 
        ForeignKey(
            'invoice.guid', 
            ondelete='CASCADE', onupdate='CASCADE'
        ), 
        index=True,
        nullable=False,
    )
    #: the guid of target transaction to refund/reverse to
    reference_to_guid = Column(
        Unicode(64), 
        ForeignKey(
            'transaction.guid', 
            ondelete='CASCADE', onupdate='CASCADE'
        ), 
        index=True,
    )
    #: what type of transaction it is, 0=charge, 1=refund, 2=payout, 3=reversal
    transaction_type = Column(Integer, index=True, nullable=False)
    #: the URI of transaction record in payment processing system
    processor_uri = Column(Unicode(128), index=True)
    #: the statement to appear on customer's transaction record (either 
    #  bank account or credit card)
    appears_on_statement_as = Column(Unicode(32))    
    #: current status of this transaction, could be
    #  0=init, 1=retrying, 2=done, 3=failed, 4=canceled
    status = Column(Integer, index=True, nullable=False)
    #: the amount to do transaction (charge, payout or refund)
    amount = Column(Integer, nullable=False)
    #: the funding instrument URI
    funding_instrument_uri = Column(Unicode(128), index=True)
    #: the created datetime of this subscription 
    created_at = Column(DateTime, default=now_func)
    #: the updated datetime of this subscription 
    updated_at = Column(DateTime, default=now_func)

    #: target transaction of refund/reverse transaction
    reference_to = relationship(
        'Transaction', 
        cascade='all, delete-orphan', 
        backref=backref('reference_from', uselist=False), 
        remote_side=[guid], 
        uselist=False, 
        single_parent=True,
    )

    #: transaction failures
    failures = relationship(
        'TransactionFailure', 
        cascade='all, delete-orphan', 
        backref='transaction',
        order_by='TransactionFailure.created_at',
        lazy='dynamic',  # so that we can query count on it
    )

    @property
    def failure_count(self):
        """Count of failures

        """
        return self.failures.count()


class TransactionFailure(DeclarativeBase):
    """A failure of transaction 

    """
    __tablename__ = 'transaction_failure'

    guid = Column(Unicode(64), primary_key=True)

    #: the guid of transaction which owns this failure
    transaction_guid = Column(
        Unicode(64), 
        ForeignKey(
            'transaction.guid', 
            ondelete='CASCADE', onupdate='CASCADE'
        ), 
        index=True,
        nullable=False,
    )

    #: error message when failed
    error_message = Column(UnicodeText)
    #: error number
    error_number = Column(Integer)
    #: error code
    error_code = Column(Unicode(64))
    #: the created datetime of this failure
    created_at = Column(DateTime, default=now_func)
