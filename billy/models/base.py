from __future__ import unicode_literals
import logging


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
