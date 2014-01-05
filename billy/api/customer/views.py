from __future__ import unicode_literals

import transaction as db_transaction
from pyramid.view import view_config
from pyramid.view import view_defaults
from pyramid.httpexceptions import HTTPNotFound
from pyramid.httpexceptions import HTTPForbidden
from pyramid.httpexceptions import HTTPBadRequest

from billy.models.customer import CustomerModel
from billy.models.invoice import InvoiceModel
from billy.models.subscription import SubscriptionModel
from billy.models.transaction import TransactionModel
from billy.api.auth import auth_api_key
from billy.api.utils import validate_form
from billy.api.utils import list_by_context
from .forms import CustomerCreateForm


def get_and_check_customer(request, company):
    """Get and check permission to access a customer

    """
    model = request.model_factory.create_customer_model()
    guid = request.matchdict['customer_guid']
    customer = model.get(guid)
    if customer is None:
        raise HTTPNotFound('No such customer {}'.format(guid))
    if customer.company_guid != company.guid:
        raise HTTPForbidden('You have no permission to access customer {}'
                            .format(guid))
    return customer 


class CustomerIndexResource(object):

    def __init__(self, request):
        self.request = request
    
    # TODO: set ACL here

    def __getitem__(self, key):
        model = self.request.model_factory.create_customer_model()
        #customer = get_and_check_customer(self.request, company)
        customer = model.get(key)
        if customer is None:
            raise HTTPNotFound('No such customer {}'.format(key))
        return CustomerResource(customer)


class CustomerResource(object):
    def __init__(self, customer):
        self.customer = customer
    # TODO: set ACL here


@view_defaults(
    route_name='customer_index', 
    context=CustomerIndexResource, 
    renderer='json',
)
class CustomerIndexView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    @view_config(request_method='GET')
    def get(self):
        request = self.request
        company = auth_api_key(request)
        return list_by_context(request, CustomerModel, company)

    @view_config(request_method='POST')
    def post(self):
        request = self.request
        company = auth_api_key(request)
        form = validate_form(CustomerCreateForm, request)
        
        processor_uri = form.data.get('processor_uri')

        # TODO: make sure user cannot create a customer to a deleted company

        model = request.model_factory.create_customer_model()
        with db_transaction.manager:
            customer = model.create(
                processor_uri=processor_uri,
                company=company, 
            )
        return customer


@view_defaults(route_name='customer_index', context=CustomerResource, renderer='json')
class CustomerView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    @view_config(request_method='GET')
    def get(self):
        customer = self.context.customer
        return customer 

    @view_config(request_method='DELETE')
    def delete(self):
        model = self.request.model_factory.create_customer_model()
        customer = self.context.customer
        if customer.deleted:
            return HTTPBadRequest('Customer {} was already deleted'
                                  .format(customer.guid))
        with db_transaction.manager:
            model.delete(customer)
        return customer

    @view_config(name='invoices')
    def invoice_index(self):
        """Get and return the list of invoices unrder current customer

        """
        customer = self.context.customer
        return list_by_context(self.request, InvoiceModel, customer)

    @view_config(name='subscriptions')
    def subscription_index(self):
        """Get and return the list of subscriptions unrder current customer

        """
        customer = self.context.customer
        return list_by_context(self.request, SubscriptionModel, customer)

    @view_config(name='transactions')
    def transaction_index(self):
        """Get and return the list of transactions unrder current customer

        """
        customer = self.context.customer
        return list_by_context(self.request, TransactionModel, customer)


def customer_index_root(request):
    return CustomerIndexResource(request)
