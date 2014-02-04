from __future__ import unicode_literals

from sqlalchemy import Column
from sqlalchemy import Unicode
from sqlalchemy import Boolean
from sqlalchemy.orm import relationship

from .base import DeclarativeBase
from .base import UTCDateTime
from .base import now_func


class Company(DeclarativeBase):
    """A Company is basically a user to billy system

    """
    __tablename__ = 'company'

    guid = Column(Unicode(64), primary_key=True)
    #: the API key for accessing billy system
    api_key = Column(Unicode(64), unique=True, index=True, nullable=False)
    #: the processor key (it would be balanced API key if we are using balanced)
    processor_key = Column(Unicode(64), index=True, nullable=False)
    #: the name of callback in URI like /v1/callback/<KEY GOES HERE>
    callback_key = Column(Unicode(64), index=True, unique=True, nullable=False)
    #: a short optional name of this company
    name = Column(Unicode(128))
    #: is this company deleted?
    deleted = Column(Boolean, default=False, nullable=False)
    #: the created datetime of this company
    created_at = Column(UTCDateTime, default=now_func)
    #: the updated datetime of this company
    updated_at = Column(UTCDateTime, default=now_func)

    #: plans of this company
    plans = relationship('Plan', cascade='all, delete-orphan',
                         backref='company')
    #: customers of this company
    customers = relationship('Customer', cascade='all, delete-orphan',
                             backref='company')

__all__ = [
    Company.__name__,
]
