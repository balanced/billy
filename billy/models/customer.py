from __future__ import unicode_literals

from billy.models import tables
from billy.models.base import BaseTableModel
from billy.models.base import decorate_offset_limit
from billy.utils.generic import make_guid


class CustomerModel(BaseTableModel):

    TABLE = tables.Customer

    # not set object
    NOT_SET = object()

    @decorate_offset_limit
    def list_by_company_guid(self, company_guid, processor_uri=NOT_SET):
        """Get invoices of a company by given guid

        """
        Customer = tables.Customer
        query = (
            self.session
            .query(Customer)
            .filter(Customer.company_guid == company_guid)
            .order_by(tables.Customer.created_at.desc())
        )
        if processor_uri is not self.NOT_SET:
            query = query.filter(Customer.processor_uri == processor_uri)
        return query

    def create(
        self, 
        company_guid, 
        processor_uri=None,
    ):
        """Create a customer and return its id

        """
        now = tables.now_func()
        customer = tables.Customer(
            guid='CU' + make_guid(),
            company_guid=company_guid,
            processor_uri=processor_uri, 
            created_at=now,
            updated_at=now,
        )
        self.session.add(customer)
        self.session.flush()

        if customer.processor_uri is None:
            # TODO:
            #customer.processor_uri = processor.create_customer(customer)
            pass
        else:
            pass
        # TODO: create corresponding customer in processor, or validate it

        self.session.flush()
        return customer.guid

    def update(self, guid, **kwargs):
        """Update a customer 

        """
        customer = self.get(guid, raise_error=True)
        now = tables.now_func()
        customer.updated_at = now
        for key in ['processor_uri']:
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
