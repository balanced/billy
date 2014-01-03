from __future__ import unicode_literals

import transaction as db_transaction
from pyramid.view import view_config
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


@view_config(route_name='customer_list', 
             request_method='GET', 
             renderer='json')
def customer_list_get(request):
    """Get and return the list of customer

    """
    company = auth_api_key(request)
    return list_by_context(request, CustomerModel, company)


@view_config(route_name='customer_invoice_list', 
             request_method='GET', 
             renderer='json')
def customer_invoice_list_get(request):
    """Get and return the list of invoices unrder given customer

    """
    company = auth_api_key(request)
    customer = get_and_check_customer(request, company)
    return list_by_context(request, InvoiceModel, customer)


@view_config(route_name='customer_subscription_list', 
             request_method='GET', 
             renderer='json')
def customer_subscription_list_get(request):
    """Get and return the list of subscriptions unrder given customer

    """
    company = auth_api_key(request)
    customer = get_and_check_customer(request, company)
    return list_by_context(request, SubscriptionModel, customer)


@view_config(route_name='customer_transaction_list', 
             request_method='GET', 
             renderer='json')
def customer_transaction_list_get(request):
    """Get and return the list of transactions unrder given customer

    """
    company = auth_api_key(request)
    customer = get_and_check_customer(request, company)
    return list_by_context(request, TransactionModel, customer)


@view_config(route_name='customer_list', 
             request_method='POST', 
             renderer='json')
def customer_list_post(request):
    """Create a new customer 

    """
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


@view_config(route_name='customer', 
             request_method='GET', 
             renderer='json')
def customer_get(request):
    """Get and return a customer 

    """
    company = auth_api_key(request)
    customer = get_and_check_customer(request, company)
    return customer 


@view_config(route_name='customer', 
             request_method='DELETE', 
             renderer='json')
def customer_delete(request):
    """Delete and return customer

    """
    company = auth_api_key(request)
    model = request.model_factory.create_customer_model()
    customer = get_and_check_customer(request, company)
    if customer.deleted:
        return HTTPBadRequest('Customer {} was already deleted'
                              .format(customer.guid))
    with db_transaction.manager:
        model.delete(customer)
    return customer
