from __future__ import unicode_literals
import logging

from billy.models import tables
from billy.utils.generic import make_guid
from billy.utils.generic import make_api_key


class CompanyModel(object):

    def __init__(self, session, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.session = session

    def get(self, guid, raise_error=False, ignore_deleted=True):
        """Find a company by guid and return it

        :param guid: The guild of company to get
        :param raise_error: Raise KeyError when cannot find one
        """
        query = (
            self.session.query(tables.Company)
            .filter_by(guid=guid)
            .filter_by(deleted=not ignore_deleted)
            .first()
        )
        if raise_error and query is None:
            raise KeyError('No such company {}'.format(guid))
        return query

    def get_by_api_key(self, api_key, raise_error=False, ignore_deleted=True):
        """Get a company by its API key

        """
        query = (
            self.session.query(tables.Company)
            .filter_by(api_key=api_key)
            .filter_by(deleted=not ignore_deleted)
            .first()
        )
        if raise_error and query is None:
            raise KeyError('No such company with API key {}'.format(api_key))
        return query

    def create(self, processor_key, name=None):
        """Create a company and return its id

        """
        now = tables.now_func()
        company = tables.Company(
            guid='CP' + make_guid(),
            processor_key=processor_key,
            api_key=make_api_key(),
            name=name, 
            created_at=now,
            updated_at=now,
        )
        self.session.add(company)
        self.session.flush()
        return company.guid

    def update(self, guid, **kwargs):
        """Update a company

        """
        company = self.get(guid, raise_error=True)
        now = tables.now_func()
        company.updated_at = now
        for key in ['name', 'processor_key', 'api_key']:
            if key not in kwargs:
                continue
            value = kwargs.pop(key)
            setattr(company, key, value)
        if kwargs:
            raise TypeError('Unknown attributes {} to update'.format(tuple(kwargs.keys())))
        self.session.add(company)
        self.session.flush()

    def delete(self, guid):
        """Delete a company

        """
        company = self.get(guid, raise_error=True)
        company.deleted = True
        self.session.add(company)
        self.session.flush()
