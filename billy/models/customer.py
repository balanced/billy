from __future__ import unicode_literals
import logging

from billy.models import tables
from billy.utils.generic import make_guid


class CustomerModel(object):

    def __init__(self, session, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.session = session

    def get(self, guid, raise_error=False, ignore_deleted=True):
        """Find a customer by guid and return it

        :param guid: The guild of customer to get
        :param raise_error: Raise KeyError when cannot find one
        """
        query = self.session.query(tables.Customer) \
            .filter_by(guid=guid) \
            .filter_by(deleted=not ignore_deleted) \
            .first()
        if raise_error and query is None:
            raise KeyError('No such customer {}'.format(guid))
        return query

    def create(
        self, 
        company_guid, 
        payment_uri, 
        name=None, 
        external_id=None
    ):
        """Create a customer and return its id

        """
        customer = tables.Customer(
            guid='CU' + make_guid(),
            company_guid=company_guid,
            payment_uri=payment_uri,
            external_id=external_id, 
            name=name, 
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
        for key in ['name', 'payment_uri', 'external_id']:
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
