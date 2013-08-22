from __future__ import unicode_literals

import transaction as db_transaction
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPNotFound
from pyramid.httpexceptions import HTTPForbidden

from billy.models.customer import CustomerModel
from billy.api.auth import auth_api_key


@view_config(route_name='customer_list', 
             request_method='GET', 
             renderer='json')
def customer_list_get(request):
    """Get and return the list of customer

    """
    # TODO:


@view_config(route_name='customer_list', 
             request_method='POST', 
             renderer='json')
def customer_list_post(request):
    """Create a new customer 

    """
    company = auth_api_key(request)
    model = CustomerModel(request.session)
    # TODO: do validation here
    external_id = request.params.get('external_id')
    company_guid = company.guid
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
    model = CustomerModel(request.session)
    guid = request.matchdict['customer_guid']
    customer = model.get(guid)
    if customer is None:
        return HTTPNotFound('No such customer {}'.format(guid))
    if customer.company_guid != company.guid:
        return HTTPForbidden('You have no permission to access customer {}'
                             .format(guid))
    return customer 
