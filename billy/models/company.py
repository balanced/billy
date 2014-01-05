from __future__ import unicode_literals

from billy.models import tables
from billy.models.base import BaseTableModel
from billy.utils.generic import make_guid
from billy.utils.generic import make_api_key


class CompanyModel(BaseTableModel):

    TABLE = tables.Company

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
        """Create a company and return

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
        return company

    def update(self, company, **kwargs):
        """Update a company

        """
        now = tables.now_func()
        company.updated_at = now
        for key in ['name', 'processor_key', 'api_key']:
            if key not in kwargs:
                continue
            value = kwargs.pop(key)
            setattr(company, key, value)
        if kwargs:
            raise TypeError('Unknown attributes {} to update'.format(tuple(kwargs.keys())))
        self.session.flush()

    def delete(self, company):
        """Delete a company

        """
        company.deleted = True
        self.session.flush()
