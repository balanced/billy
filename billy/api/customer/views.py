import transaction as db_transaction
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPNotFound

from billy.models.customer import CustomerModel


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
    model = CustomerModel(request.session)
    # TODO: do validation here
    external_id = request.params.get('external_id')
    # TODO: company guid should be retrived from API key
    # this is just a temporary hack for development
    company_guid = request.params.get('company_guid')
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
    model = CustomerModel(request.session)
    guid = request.matchdict['customer_guid']
    customer = model.get(guid)
    if customer is None:
        return HTTPNotFound('No such customer {}'.format(guid))
    return customer 
