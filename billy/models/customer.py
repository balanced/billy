from __future__ import unicode_literals

from billy.db import tables
from billy.models.base import BaseTableModel
from billy.models.base import decorate_offset_limit
from billy.utils.generic import make_guid


class CustomerModel(BaseTableModel):

    TABLE = tables.Customer

    # not set object
    NOT_SET = object()

    @decorate_offset_limit
    def list_by_context(self, context, processor_uri=NOT_SET):
        """List customer by a given context

        """
        Company = tables.Company
        Customer = tables.Customer
        Plan = tables.Plan
        Subscription = tables.Subscription

        query = self.session.query(Customer)
        if isinstance(context, Plan):
            query = (
                query
                .join(
                    Subscription,
                    Subscription.customer_guid == Customer.guid,
                )
                .filter(Subscription.plan == context)
            )
        elif isinstance(context, Company):
            query = query.filter(Customer.company == context)
        else:
            raise ValueError('Unsupported context {}'.format(context))

        if processor_uri is not self.NOT_SET:
            query = query.filter(Customer.processor_uri == processor_uri)
        query = query.order_by(Customer.created_at.desc())
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
        processor.configure_api_key(customer.company.processor_key)
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
