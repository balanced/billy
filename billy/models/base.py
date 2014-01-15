from __future__ import unicode_literals
import logging
from functools import wraps


def decorate_offset_limit(func):
    """Make a querying function accept extra optional offset and limit
    parameter and set to the querying result

    """
    @wraps(func)
    def callee(*args, **kwargs):
        try:
            offset = kwargs.pop('offset')
        except KeyError:
            offset = None
        try:
            limit = kwargs.pop('limit')
        except KeyError:
            limit = None
        query = func(*args, **kwargs)
        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)
        return query
    return callee


class BaseTableModel(object):

    #: the table for this model
    TABLE = None

    def __init__(self, factory, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.factory = factory
        self.session = factory.session
        assert self.TABLE is not None

    def get(self, guid, raise_error=False, with_lockmode=None):
        """Find a record by guid and return it

        :param guid: The guild of record to get
        :param raise_error: Raise KeyError when cannot find one
        :param with_lockmode: The lock model to acquire on the row
        """
        query = self.session.query(self.TABLE)
        if with_lockmode is not None:
            query = query.with_lockmode(with_lockmode)
        query = query.get(guid)
        if raise_error and query is None:
            raise KeyError('No such {} {}'.format(
                self.TABLE.__name__.lower(), guid
            ))
        return query
