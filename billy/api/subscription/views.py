from __future__ import unicode_literals

import transaction as db_transaction
from pyramid.view import view_config
from pyramid.settings import asbool
from pyramid.httpexceptions import HTTPNotFound
from pyramid.httpexceptions import HTTPForbidden
from pyramid.httpexceptions import HTTPBadRequest

from billy.models.subscription import SubscriptionModel
from billy.models.transaction import TransactionModel
from billy.api.auth import auth_api_key
from billy.api.utils import validate_form
from billy.api.utils import form_errors_to_bad_request
from billy.api.utils import list_by_context
from .forms import SubscriptionCreateForm
from .forms import SubscriptionCancelForm


def get_and_check_subscription(request, company, guid):
    """Get and check permission to access a subscription

    """
    model = request.model_factory.create_subscription_model()
    subscription = model.get(guid)
    if subscription is None:
        raise HTTPNotFound('No such subscription {}'.format(guid))
    if subscription.customer.company != company:
        raise HTTPForbidden('You have no permission to access subscription {}'
                            .format(guid))
    return subscription


@view_config(route_name='subscription_list', 
             request_method='GET', 
             renderer='json')
def subscription_list_get(request):
    """Get and return subscriptions

    """
    company = auth_api_key(request)
    return list_by_context(request, SubscriptionModel, company)


@view_config(route_name='subscription_transaction_list', 
             request_method='GET', 
             renderer='json')
def subscription_transaction_list(request):
    """Get and return transactions of subscription

    """
    company = auth_api_key(request)
    guid = request.matchdict['subscription_guid']
    subscription = get_and_check_subscription(request, company, guid)
    return list_by_context(request, TransactionModel, subscription)


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
    funding_instrument_uri = form.data.get('funding_instrument_uri')
    if not funding_instrument_uri:
        funding_instrument_uri = None
    appears_on_statement_as = form.data.get('appears_on_statement_as')
    if not appears_on_statement_as:
        appears_on_statement_as = None
    started_at = form.data.get('started_at')

    sub_model = request.model_factory.create_subscription_model()
    plan_model = request.model_factory.create_plan_model()
    customer_model = request.model_factory.create_customer_model()
    tx_model = request.model_factory.create_transaction_model()

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
        subscription = sub_model.create(
            customer=customer, 
            plan=plan, 
            amount=amount, 
            funding_instrument_uri=funding_instrument_uri,
            appears_on_statement_as=appears_on_statement_as,
            started_at=started_at, 
        )
        transactions = sub_model.yield_transactions([subscription])
    # this is not a deferred subscription, just process transactions right away
    if started_at is None:
        with db_transaction.manager:
            tx_model.process_transactions(transactions)

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
    appears_on_statement_as = form.data.get('appears_on_statement_as')
    if not appears_on_statement_as:
        appears_on_statement_as = None

    sub_model = request.model_factory.create_subscription_model()
    tx_model = request.model_factory.create_transaction_model()
    get_and_check_subscription(request, company, guid)
    subscription = sub_model.get(guid)

    # TODO: maybe we can find a better way to integrate this with the 
    # form validation?
    if refund_amount is not None:
        amount = subscription.effective_amount
        if refund_amount > amount:
            return form_errors_to_bad_request(dict(
                refund_amount=['refund_amount cannot be greater than '
                               'subscription amount {}'.format(amount)]
            ))

    if subscription.canceled:
        return HTTPBadRequest('Cannot cancel a canceled subscription')

    with db_transaction.manager:
        transaction = sub_model.cancel(
            subscription, 
            prorated_refund=prorated_refund,
            refund_amount=refund_amount, 
            appears_on_statement_as=appears_on_statement_as,
        )
    if transaction is not None:
        with db_transaction.manager:
            tx_model.process_transactions([transaction])

    return subscription 
