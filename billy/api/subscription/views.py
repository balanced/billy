from __future__ import unicode_literals

import transaction as db_transaction
from pyramid.view import view_config
from pyramid.settings import asbool
from pyramid.httpexceptions import HTTPNotFound
from pyramid.httpexceptions import HTTPForbidden
from pyramid.httpexceptions import HTTPBadRequest

from billy.models.customer import CustomerModel 
from billy.models.plan import PlanModel
from billy.models.subscription import SubscriptionModel 
from billy.models.transaction import TransactionModel 
from billy.api.auth import auth_api_key
from billy.api.utils import validate_form
from billy.api.utils import form_errors_to_bad_request
from billy.api.utils import list_by_company_guid
from .forms import SubscriptionCreateForm
from .forms import SubscriptionCancelForm


def get_and_check_subscription(request, company, guid):
    """Get and check permission to access a subscription

    """
    model = SubscriptionModel(request.session)
    subscription = model.get(guid)
    if subscription is None:
        raise HTTPNotFound('No such subscription {}'.format(guid))
    if subscription.customer.company_guid != company.guid:
        raise HTTPForbidden('You have no permission to access subscription {}'
                            .format(guid))
    return subscription


@view_config(route_name='subscription_list', 
             request_method='GET', 
             renderer='json')
def subscription_list_get(request):
    """Get and return subscriptions

    """
    return list_by_company_guid(request, SubscriptionModel)


@view_config(route_name='subscription_list', 
             request_method='POST', 
             renderer='json')
def subscription_list_post(request):
    """Create a new subscription 

    """
    company = auth_api_key(request)
    form = validate_form(SubscriptionCreateForm, request)

    customer_guid = form.data['customer_guid']
    plan_guid = form.data['plan_guid']
    amount = form.data.get('amount')
    payment_uri = form.data.get('payment_uri')
    started_at = form.data.get('started_at')
    maximum_retry = int(request.registry.settings.get(
        'billy.transaction.maximum_retry', 
        TransactionModel.DEFAULT_MAXIMUM_RETRY,
    ))

    model = SubscriptionModel(request.session)
    plan_model = PlanModel(request.session)
    customer_model = CustomerModel(request.session)
    tx_model = TransactionModel(request.session)

    customer = customer_model.get(customer_guid)
    if customer.company_guid != company.guid:
        return HTTPForbidden('Can only subscribe to your own customer')
    if customer.deleted:
        return HTTPBadRequest('Cannot subscript to a deleted customer')
    plan = plan_model.get(plan_guid)
    if plan.company_guid != company.guid:
        return HTTPForbidden('Can only subscribe to your own plan')
    if plan.deleted:
        return HTTPBadRequest('Cannot subscript to a deleted plan')

    # create subscription and yield transactions
    with db_transaction.manager:
        guid = model.create(
            customer_guid=customer_guid, 
            plan_guid=plan_guid, 
            amount=amount, 
            payment_uri=payment_uri,
            started_at=started_at, 
        )
        tx_guids = model.yield_transactions([guid])
    # this is not a deferred subscription, just process transactions right away
    if started_at is None:
        with db_transaction.manager:
            tx_model.process_transactions(
                processor=request.processor, 
                guids=tx_guids,
                maximum_retry=maximum_retry,
            )

    subscription = model.get(guid)
    return subscription


@view_config(route_name='subscription', 
             request_method='GET', 
             renderer='json')
def subscription_get(request):
    """Get and return a subscription 

    """
    company = auth_api_key(request)
    guid = request.matchdict['subscription_guid']
    subscription = get_and_check_subscription(request, company, guid)
    return subscription 


@view_config(route_name='subscription_transaction_list', 
             request_method='GET', 
             renderer='json')
def subscription_transaction_list(request):
    """Get and return transactions of subscription

    """
    company = auth_api_key(request)

    offset = int(request.params.get('offset', 0))
    limit = int(request.params.get('limit', 20))
    guid = request.matchdict['subscription_guid']

    tx_model = TransactionModel(request.session)
    subscription = get_and_check_subscription(request, company, guid)

    transactions = tx_model.list_by_subscription_guid(
        subscription_guid=subscription.guid,
        offset=offset,
        limit=limit,
    )
    result = dict(
        items=list(transactions),
        offset=offset,
        limit=limit,
    )
    return result


@view_config(route_name='subscription_cancel', 
             request_method='POST', 
             renderer='json')
def subscription_cancel(request):
    """Cancel a subscription

    """
    # TODO: it appears a DELETE request with body is not a good idea
    # for HTTP protocol as many server doesn't support this, this is why
    # we use another view with post method, maybe we should use a better 
    # approach later
    company = auth_api_key(request)
    form = validate_form(SubscriptionCancelForm, request)

    guid = request.matchdict['subscription_guid']
    prorated_refund = asbool(form.data.get('prorated_refund', False))
    refund_amount = form.data.get('refund_amount')
    maximum_retry = int(request.registry.settings.get(
        'billy.transaction.maximum_retry', 
        TransactionModel.DEFAULT_MAXIMUM_RETRY,
    ))

    model = SubscriptionModel(request.session)
    tx_model = TransactionModel(request.session)
    get_and_check_subscription(request, company, guid)
    subscription = model.get(guid)

    # TODO: maybe we can find a better way to integrate this with the 
    # form validation?
    if refund_amount is not None:
        if subscription.amount is not None:
            amount = subscription.amount
        else:
            amount = subscription.plan.amount
        if refund_amount > amount:
            return form_errors_to_bad_request(dict(
                refund_amount=['refund_amount cannot be greater than '
                               'subscription amount {}'.format(amount)]
            ))

    if subscription.canceled:
        return HTTPBadRequest('Cannot cancel a canceled subscription')

    with db_transaction.manager:
        tx_guid = model.cancel(
            guid, 
            prorated_refund=prorated_refund,
            refund_amount=refund_amount, 
        )
    if tx_guid is not None:
        with db_transaction.manager:
            tx_model.process_transactions(
                processor=request.processor, 
                guids=[tx_guid],
                maximum_retry=maximum_retry,
            )

    subscription = model.get(guid)
    return subscription 
