from __future__ import unicode_literals
import json
from datetime import datetime

from dateutil.relativedelta import relativedelta
from sqlalchemy import Column, DateTime, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.types import TypeDecorator, VARCHAR

from settings import Session


class Base(object):

    query = Session.query_property()
    session = Session

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow, nullable=False)

Base = declarative_base(cls=Base)


class RelativeDelta(TypeDecorator):

    """
    A python dictionary to json type
    """
    impl = VARCHAR

    def from_relativedelta(self, inter):
        return {
            'years': inter.years,
            'months': inter.months,
            'days': inter.days,
            'hours': inter.hours,
        }

    def to_relativedelta(self, param):
        return relativedelta(years=param['years'], months=param['months'],
                             days=param['days'], hours=param['hours'])

    def process_bind_param(self, value, dialect):
        if value and not isinstance(value, relativedelta):
            raise ValueError("Accepts only relativedelta types")
        if value:
            data_json = self.from_relativedelta(value)
            value = json.dumps(data_json)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            data = json.loads(value)
            value = self.to_relativedelta(data)
        return value
