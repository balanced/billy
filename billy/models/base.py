from __future__ import unicode_literals

from dateutil.relativedelta import relativedelta
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.types import TypeDecorator, VARCHAR
import ujson

from settings import Session

Base = declarative_base()
Base.query = Session.query_property()
Base.session = Session


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
        if not isinstance(value, relativedelta):
            raise ValueError("Accepts only relativedelta types")
        if value is not None:
            data_json = self.from_relativedelta(value)
            value = ujson.dumps(data_json)

        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            data = ujson.loads(value)
            value = self.to_relativedelta(data)
        return value
