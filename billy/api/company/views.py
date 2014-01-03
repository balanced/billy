from __future__ import unicode_literals

import transaction as db_transaction
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPNotFound
from pyramid.httpexceptions import HTTPForbidden

from billy.api.auth import auth_api_key
from billy.api.utils import validate_form
from .forms import CompanyCreateForm


@view_config(route_name='company_list', 
             request_method='POST', 
             renderer='json')
def company_list_post(request):
    """Create a new company

    """
    form = validate_form(CompanyCreateForm, request)
    processor_key = form.data['processor_key']
    # TODO: validate API key in processor?

    model = request.model_factory.create_company_model()
    with db_transaction.manager:
        company = model.create(processor_key=processor_key)
    return company


@view_config(route_name='company', 
             request_method='GET', 
             renderer='json')
def company_get(request):
    """Get and return a company

    """
    api_company = auth_api_key(request)
    model = request.model_factory.create_company_model()
    guid = request.matchdict['company_guid']
    company = model.get(guid)
    if company is None:
        return HTTPNotFound('No such company {}'.format(guid))
    if guid != api_company.guid:
        return HTTPForbidden('You have no premission to access company {}'.format(guid))
    return company
