from __future__ import unicode_literals

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPNotFound
from pyramid.httpexceptions import HTTPForbidden

from billy.models.transaction import TransactionModel 
from billy.api.auth import auth_api_key


@view_config(route_name='transaction_list', 
             request_method='GET', 
             renderer='json')
def transaction_list_get(request):
    """Get and return transactions

    """
    company = auth_api_key(request)
    model = TransactionModel(request.session)
    offset = int(request.params.get('offset', 0))
    limit = int(request.params.get('limit', 20))
    transactions = model.list_by_company_guid(
        company_guid=company.guid,
        offset=offset,
        limit=limit,
    )
    result = dict(
        items=list(transactions),
        offset=offset,
        limit=limit,
    )
    return result


@view_config(route_name='transaction', 
             request_method='GET', 
             renderer='json')
def transaction_get(request):
    """Get and return a transaction 

    """
    company = auth_api_key(request)
    model = TransactionModel(request.session)
    guid = request.matchdict['transaction_guid']
    transaction = model.get(guid)
    if transaction is None:
        return HTTPNotFound('No such transaction {}'.format(guid))
    if transaction.subscription.customer.company_guid != company.guid:
        return HTTPForbidden('You have no permission to access transaction {}'
                             .format(guid))
    return transaction 
