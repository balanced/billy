from __future__ import unicode_literals
import logging

from billy.models import tables
from billy.utils.generic import make_guid
from billy.utils.generic import make_api_key


class CompanyModel(object):

    def __init__(self, session, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.session = session

    def get_company_by_guid(self, guid, raise_error=False, ignore_deleted=True):
        """Find a company by guid and return it

        :param guid: The guild of company to get
        :param raise_error: Raise KeyError when cannot find one
        """
        query = self.session.query(tables.Company) \
            .filter_by(guid=guid) \
            .filter_by(deleted=not ignore_deleted) \
            .first()
        if raise_error and query is None:
            raise KeyError('No such company {}'.format(guid))
        return query

    def create_company(self, processor_key, name=None):
        """Create a company and return its id

        """
        company = tables.Company(
            guid='CP' + make_guid(),
            processor_key=processor_key,
            api_key=make_api_key(),
            name=name, 
        )
        self.session.add(company)
        self.session.flush()
        return company.guid

    def update_company(self, guid, **kwargs):
        """Update a company

        """
        company = self.get_company_by_guid(guid, raise_error=True)
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

    def delete_company(self, guid):
        """Delete a company

        """
        company = self.get_company_by_guid(guid, raise_error=True)
        company.deleted = True
        self.session.add(company)
        self.session.flush()
