from __future__ import unicode_literals

from pyramid.view import view_config
from pyramid.view import view_defaults
from pyramid.security import Allow
from pyramid.security import Authenticated
from pyramid.security import authenticated_userid
from pyramid.httpexceptions import HTTPNotFound

from billy.models.transaction import TransactionModel 
from billy.api.utils import list_by_context


class TransactionIndexResource(object):
    __acl__ = [
        #       principal      action
        (Allow, Authenticated, 'view'),
        (Allow, Authenticated, 'create'),
    ]

    def __init__(self, request):
        self.request = request

    def __getitem__(self, key):
        model = self.request.model_factory.create_transaction_model()
        transaction = model.get(key)
        if transaction is None:
            raise HTTPNotFound('No such transaction {}'.format(key))
        return TransactionResource(transaction)


class TransactionResource(object):
    def __init__(self, transaction):
        self.transaction = transaction 
        # make sure only the owner company can access the customer
        if self.transaction.transaction_cls == TransactionModel.CLS_SUBSCRIPTION:
            company = self.transaction.subscription.plan.company
        else:
            company = self.transaction.invoice.customer.company
        company_principal = 'company:{}'.format(company.guid)
        self.__acl__ = [
            #       principal          action
            (Allow, company_principal, 'view'),
        ]


@view_defaults(
    route_name='transaction_index', 
    context=TransactionIndexResource, 
    renderer='json',
)
class TransactionIndexView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    @view_config(request_method='GET', permission='view')
    def get(self):
        request = self.request
        company = authenticated_userid(request)
        return list_by_context(request, TransactionModel, company)


@view_defaults(
    route_name='transaction_index', 
    context=TransactionResource, 
    renderer='json',
)
class TransactionView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    @view_config(request_method='GET')
    def get(self):
        return self.context.transaction


def transaction_index_root(request):
    return TransactionIndexResource(request)
