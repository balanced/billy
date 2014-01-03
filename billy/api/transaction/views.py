from __future__ import unicode_literals

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPNotFound
from pyramid.httpexceptions import HTTPForbidden

from billy.models.transaction import TransactionModel 
from billy.api.auth import auth_api_key
from billy.api.utils import list_by_context


@view_config(route_name='transaction_list', 
             request_method='GET', 
             renderer='json')
def transaction_list_get(request):
    """Get and return transactions

    """
    company = auth_api_key(request)
    return list_by_context(request, TransactionModel, company)


@view_config(route_name='transaction', 
             request_method='GET', 
             renderer='json')
def transaction_get(request):
    """Get and return a transaction 

    """
    company = auth_api_key(request)
    model = request.model_factory.create_transaction_model()
    guid = request.matchdict['transaction_guid']
    transaction = model.get(guid)
    if transaction is None:
        return HTTPNotFound('No such transaction {}'.format(guid))
    if transaction.subscription.customer.company_guid != company.guid:
        return HTTPForbidden('You have no permission to access transaction {}'
                             .format(guid))
    return transaction 
