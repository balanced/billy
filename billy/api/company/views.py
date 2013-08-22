import transaction as db_transaction
from pyramid.view import view_config

from billy.models.company import CompanyModel


@view_config(route_name='company_list', 
             request_method='GET', 
             renderer='json')
def company_list_get(request):
    """Get and return the list of company

    """
    # TODO:


@view_config(route_name='company_list', 
             request_method='POST', 
             renderer='json')
def company_list_post(request):
    """Create a new company

    """
    model = CompanyModel(request.session)
    # TODO: do validation here
    processor_key = request.params['processor_key']
    with db_transaction.manager:
        guid = model.create(processor_key=processor_key)
    company = model.get(guid)
    return company


@view_config(route_name='company', 
             request_method='GET', 
             renderer='json')
def company_get(request):
    """Get and return a company

    """
    model = CompanyModel(request.session)
    guid = request.matchdict['company_guid']
    company = model.get(guid)
    return company
