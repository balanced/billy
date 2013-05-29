from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.types import TypeDecorator, VARCHAR
import ujson

Base = declarative_base()



class JSONDict(TypeDecorator):
    """A json type to store intevals in.

    Usage::

        JSONEncodedDict(255)

    """

    impl = VARCHAR

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = ujson.dumps(value)

        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = ujson.loads(value)
        return value