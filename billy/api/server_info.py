from __future__ import unicode_literals

from pyramid.view import view_config
from pyramid.security import NO_PERMISSION_REQUIRED

from billy import version


@view_config(
    route_name='server_info',
    request_method='GET',
    renderer='json',
    permission=NO_PERMISSION_REQUIRED,
)
def server_info(request):
    """Get server information

    """
    tx_model = request.model_factory.create_transaction_model()
    last_transaction = tx_model.get_last_transaction()
    last_transaction_dt = None
    if last_transaction is not None:
        last_transaction_dt = last_transaction.created_at.isoformat()
    return dict(
        server='Billy - The recurring payment server',
        powered_by='BalancedPayments.com',
        version=version.VERSION,
        revision=version.REVISION,
        last_transaction_created_at=last_transaction_dt,
    )
