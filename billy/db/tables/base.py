from __future__ import unicode_literals

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

__all__ = [
    'DeclarativeBase',
    set_now_func.__name__,
    get_now_func.__name__,
    now_func.__name__,
]
