from __future__ import unicode_literals

import transaction as db_transaction
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPNotFound
from pyramid.httpexceptions import HTTPForbidden

from billy.models.company import CompanyModel
from billy.api.auth import auth_api_key


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
    api_company = auth_api_key(request)
    model = CompanyModel(request.session)
    guid = request.matchdict['company_guid']
    company = model.get(guid)
    if company is None:
        return HTTPNotFound('No such company {}'.format(guid))
    if guid != api_company.guid:
        return HTTPForbidden('You have no premission to access company {}'.format(guid))
    return company
