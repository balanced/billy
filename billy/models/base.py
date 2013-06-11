from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.types import TypeDecorator, VARCHAR
import ujson

from billy.errors import ValidationError
from billy.settings import Session

Base = declarative_base()
Base.query = Session.query_property()
Base.session = Session


class JSONDict(TypeDecorator):
    """
    A python dictionary to json type
    """
    impl = VARCHAR

    def process_bind_param(self, value, dialect):
        if not isinstance(value, dict):
            raise ValidationError("Excepts only python dicts")
        if value is not None:
            value = ujson.dumps(value)

        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = ujson.loads(value)
        return value



class JSONList(TypeDecorator):
    """
    A python dictionary to json type
    """
    impl = VARCHAR

    def process_bind_param(self, value, dialect):
        if not isinstance(value, list):
            raise ValidationError("Excepts only python lists")
        if value is not None:
            value = ujson.dumps(value)

        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = ujson.loads(value)
        return value
