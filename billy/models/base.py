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


class ListByCompanyMixin(object):

    @decorate_offset_limit
    def list_by_company_guid(self, company_guid):
        """Get records of a company by given guid

        :param company_guid: the given company GUID
        :param offset: offset for listing, None indicates no offset
        :param limit: limit for listing, None indicates no limit
        """
        assert self.TABLE is not None
        query = (
            self.session
            .query(self.TABLE)
            .filter(self.TABLE.company_guid == company_guid)
            .order_by(self.TABLE.created_at.desc())
        )
        return query


class BaseTableModel(object):

    #: the table for this model
    TABLE = None

    def __init__(self, session, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.session = session
        assert self.TABLE is not None

    def get(self, guid, raise_error=False):
        """Find a record by guid and return it

        :param guid: The guild of record to get
        :param raise_error: Raise KeyError when cannot find one
        """
        query = (
            self.session.query(self.TABLE)
            .get(guid)
        )
        if raise_error and query is None:
            raise KeyError('No such subscription {}'.format(guid))
        return query
