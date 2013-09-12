from __future__ import unicode_literals

from billy.models import tables
from billy.models.base import BaseTableModel
from billy.models.base import ListByCompanyMixin
from billy.utils.generic import make_guid


class CustomerModel(BaseTableModel, ListByCompanyMixin):

    TABLE = tables.Customer

    def create(
        self, 
        company_guid, 
        external_id=None
    ):
        """Create a customer and return its id

        """
        now = tables.now_func()
        customer = tables.Customer(
            guid='CU' + make_guid(),
            company_guid=company_guid,
            external_id=external_id, 
            created_at=now,
            updated_at=now,
        )
        self.session.add(customer)
        self.session.flush()
        return customer.guid

    def update(self, guid, **kwargs):
        """Update a customer 

        """
        customer = self.get(guid, raise_error=True)
        now = tables.now_func()
        customer.updated_at = now
        for key in ['external_id']:
            if key not in kwargs:
                continue
            value = kwargs.pop(key)
            setattr(customer, key, value)
        if kwargs:
            raise TypeError('Unknown attributes {} to update'.format(tuple(kwargs.keys())))
        self.session.add(customer)
        self.session.flush()

    def delete(self, guid):
        """Delete a customer 

        """
        customer = self.get(guid, raise_error=True)
        customer.deleted = True
        self.session.add(customer)
        self.session.flush()
