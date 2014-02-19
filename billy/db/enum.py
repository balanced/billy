from __future__ import unicode_literals
import re

from sqlalchemy import Enum
from sqlalchemy.types import SchemaType, TypeDecorator

# The following was taken from Michael Bayer's blogpost on how to
# use declarative base to declare Enums appropriately in such project
# You can read the article here:
#   http://techspot.zzzeek.org/2011/01/14/the-enum-recipe/
# You can see the recipie here:
#   http://techspot.zzzeek.org/files/2011/decl_enum.py


class DeclEnumType(SchemaType, TypeDecorator):

    def __init__(self, enum):
        super(DeclEnumType, self).__init__()
        self.enum = enum
        to_lower = lambda m: "_" + m.group(1).lower()
        self.name = 'ck{}'.format(re.sub('([A-Z])', to_lower, enum.__name__))
        self.impl = Enum(*enum.values(), name=self.name)

    def _set_table(self, table, column):
        self.impl._set_table(table, column)

    def copy(self):
        return DeclEnumType(self.enum)

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return value.value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return self.enum.from_string(value.strip())


class EnumSymbol(object):
    """Define a fixed symbol tied to a parent class."""

    def __init__(self, cls_, name, value, description):
        self.cls_ = cls_
        self.name = name
        self.value = value
        self.description = description

    def __reduce__(self):
        """Allow unpickling to return the symbol
        linked to the DeclEnum class."""
        return getattr, (self.cls_, self.name)

    def __iter__(self):
        return iter([self.value, self.description])

    def __repr__(self):
        return "%s" % self.name


class EnumMeta(type):
    """Generate new DeclEnum classes."""

    def __init__(cls, classname, bases, dict_):
        cls._reg = reg = cls._reg.copy()
        for k, v in dict_.items():
            if isinstance(v, tuple):
                sym = reg[v[0]] = EnumSymbol(cls, k, *v)
                setattr(cls, k, sym)
        return type.__init__(cls, classname, bases, dict_)

    def __iter__(cls):
        return iter(cls._reg.values())


class DeclEnum(object):
    """Declarative enumeration."""

    __metaclass__ = EnumMeta
    _reg = {}

    @classmethod
    def from_string(cls, value):
        try:
            return cls._reg[value]
        except KeyError:
            error_msg = "Invalid value for %r: %r" % (cls.__name__, value)
            raise ValueError(error_msg)

    @classmethod
    def values(cls):
        return cls._reg.keys()

    @classmethod
    def db_type(cls):
        return DeclEnumType(cls)
