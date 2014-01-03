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
    def list_by_company_guid(self, company, processor_uri=NOT_SET):
        """Get invoices of a company by given guid

        """
        Customer = tables.Customer
        query = (
            self.session
            .query(Customer)
            .filter(Customer.company == company)
            .order_by(tables.Customer.created_at.desc())
        )
        if processor_uri is not self.NOT_SET:
            query = query.filter(Customer.processor_uri == processor_uri)
        return query

    def create(
        self, 
        company, 
        processor_uri=None,
    ):
        """Create a customer and return its id

        """
        now = tables.now_func()
        customer = tables.Customer(
            guid='CU' + make_guid(),
            company=company,
            processor_uri=processor_uri, 
            created_at=now,
            updated_at=now,
        )
        self.session.add(customer)
        self.session.flush()

        processor = self.factory.create_processor()
        # create customer
        if customer.processor_uri is None:
            customer.processor_uri = processor.create_customer(customer)
        # validate the customer processor URI
        else:
            processor.validate_customer(customer.processor_uri)

        self.session.flush()
        return customer

    def update(self, customer, **kwargs):
        """Update a customer 

        """
        now = tables.now_func()
        customer.updated_at = now
        for key in ['processor_uri']:
            if key not in kwargs:
                continue
            value = kwargs.pop(key)
            setattr(customer, key, value)
        if kwargs:
            raise TypeError('Unknown attributes {} to update'.format(tuple(kwargs.keys())))
        self.session.flush()

    def delete(self, customer):
        """Delete a customer 

        """
        customer.deleted = True
        self.session.flush()
