from __future__ import unicode_literals

import transaction as db_transaction
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPNotFound
from pyramid.httpexceptions import HTTPForbidden
from pyramid.httpexceptions import HTTPBadRequest

from billy.models.customer import CustomerModel
from billy.api.auth import auth_api_key
from billy.api.utils import validate_form
from billy.api.utils import list_by_company_guid
from .forms import CustomerCreateForm


def get_and_check_customer(request, company):
    """Get and check permission to access a customer

    """
    model = CustomerModel(request.session)
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
    return list_by_company_guid(request, CustomerModel)


@view_config(route_name='customer_list', 
             request_method='POST', 
             renderer='json')
def customer_list_post(request):
    """Create a new customer 

    """
    company = auth_api_key(request)
    form = validate_form(CustomerCreateForm, request)
    
    external_id = form.data.get('external_id')
    company_guid = company.guid

    # TODO: make sure user cannot create a customer to a deleted company

    model = CustomerModel(request.session)
    # TODO: do validation here
    with db_transaction.manager:
        guid = model.create(
            external_id=external_id,
            company_guid=company_guid, 
        )
    customer = model.get(guid)
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
    model = CustomerModel(request.session)
    customer = get_and_check_customer(request, company)
    if customer.deleted:
        return HTTPBadRequest('Customer {} was already deleted'
                              .format(customer.guid))
    with db_transaction.manager:
        model.delete(customer.guid)
    customer = model.get(customer.guid)
    return customer
