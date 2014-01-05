from __future__ import unicode_literals

import transaction as db_transaction
from pyramid.view import view_config
from pyramid.view import view_defaults
from pyramid.security import Allow
from pyramid.security import Authenticated
from pyramid.security import NO_PERMISSION_REQUIRED
from pyramid.httpexceptions import HTTPNotFound

from billy.api.utils import validate_form
from .forms import CompanyCreateForm


class CompanyIndexResource(object):
    __acl__ = [
        #       principal      action
        (Allow, Authenticated, 'view'),
        (Allow, Authenticated, 'create'),
    ]

    def __init__(self, request):
        self.request = request

    def __getitem__(self, key):
        model = self.request.model_factory.create_company_model()
        company = model.get(key)
        if company is None:
            raise HTTPNotFound('No such company {}'.format(key))
        return CompanyResource(company)


class CompanyResource(object):
    def __init__(self, company):
        self.company = company
        # make sure only the owner company can access the company
        company_principal = 'company:{}'.format(self.company.guid)
        self.__acl__ = [
            #       principal          action
            (Allow, company_principal, 'view'),
        ]


@view_defaults(
    route_name='company_index', 
    context=CompanyIndexResource, 
    renderer='json',
)
class CompanyIndexView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    @view_config(request_method='POST', permission=NO_PERMISSION_REQUIRED)
    def post(self):
        request = self.request
        form = validate_form(CompanyCreateForm, request)
        processor_key = form.data['processor_key']
        # TODO: validate API key in processor?

        model = request.model_factory.create_company_model()
        with db_transaction.manager:
            company = model.create(processor_key=processor_key)
        return company


@view_defaults(
    route_name='company_index', 
    context=CompanyResource, 
    renderer='json',
)
class CustomerView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    @view_config(request_method='GET')
    def get(self):
        company = self.context.company
        return company


# TODO: replace this with a global root factory
def company_index_root(request):
    return CompanyIndexResource(request)
