from __future__ import unicode_literals

import transaction as db_transaction
from pyramid.view import view_config
from pyramid.view import view_defaults
from pyramid.security import Allow
from pyramid.security import Authenticated
from pyramid.security import authenticated_userid
from pyramid.httpexceptions import HTTPNotFound
from pyramid.httpexceptions import HTTPBadRequest

from billy.models.customer import CustomerModel
from billy.models.invoice import InvoiceModel
from billy.models.subscription import SubscriptionModel
from billy.models.transaction import TransactionModel
from billy.api.utils import validate_form
from billy.api.utils import list_by_context
from .forms import CustomerCreateForm


class CustomerIndexResource(object):
    __acl__ = [
        #       principal      action
        (Allow, Authenticated, 'view'),
        (Allow, Authenticated, 'create'),
    ]

    def __init__(self, request):
        self.request = request

    def __getitem__(self, key):
        model = self.request.model_factory.create_customer_model()
        customer = model.get(key)
        if customer is None:
            raise HTTPNotFound('No such customer {}'.format(key))
        return CustomerResource(customer)


class CustomerResource(object):
    def __init__(self, customer):
        self.customer = customer
        # make sure only the owner company can access the customer
        company_principal = 'company:{}'.format(self.customer.company.guid)
        self.__acl__ = [
            #       principal          action
            (Allow, company_principal, 'view'),
        ]


@view_defaults(
    route_name='customer_index', 
    context=CustomerIndexResource, 
    renderer='json',
)
class CustomerIndexView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    @view_config(request_method='GET', permission='view')
    def get(self):
        request = self.request
        company = authenticated_userid(request)
        return list_by_context(request, CustomerModel, company)

    @view_config(request_method='POST', permission='create')
    def post(self):
        request = self.request
        company = authenticated_userid(request)
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


@view_defaults(
    route_name='customer_index', 
    context=CustomerResource, 
    renderer='json',
)
class CustomerView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    @view_config(request_method='GET')
    def get(self):
        return self.context.customer

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
