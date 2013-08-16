from __future__ import unicode_literals

from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Unicode
from sqlalchemy import UnicodeText
from sqlalchemy import Boolean
from sqlalchemy import DateTime
from sqlalchemy import Numeric
from sqlalchemy.schema import ForeignKey
from sqlalchemy.orm import relation
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

    guid = Column(String(64), primary_key=True)
    #: the API key for accessing billy system
    api_key = Column(String(64), unique=True, index=True, nullable=False)
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
    plans = relation('Plan', cascade='all, delete-orphan', backref='company')


class Plan(DeclarativeBase):
    """Plan is a recurring payment schedule, such as a hosting service plan.

    """
    __tablename__ = 'plan'

    guid = Column(String(64), primary_key=True)
    #: the guid of company which owns this plan
    company_guid = Column(
        String(64), 
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
    # TODO: this is just a rough implementation, should allow 
    # a more flexiable setting later
    frequency = Column(Integer, nullable=False)
    #: is this plan deleted?
    deleted = Column(Boolean, default=False, nullable=False)
    #: the created datetime of this plan
    created_at = Column(DateTime(timezone=True), default=now_func)
    #: the updated datetime of this plan
    updated_at = Column(DateTime(timezone=True), default=now_func)
