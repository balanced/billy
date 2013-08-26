from __future__ import unicode_literals

import transaction as db_transaction
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPNotFound
from pyramid.httpexceptions import HTTPForbidden

from billy.models.customer import CustomerModel 
from billy.models.plan import PlanModel
from billy.models.subscription import SubscriptionModel 
from billy.api.auth import auth_api_key
from billy.api.utils import validate_form
from .forms import SubscriptionCreateForm


@view_config(route_name='subscription_list', 
             request_method='POST', 
             renderer='json')
def subscription_list_post(request):
    """Create a new subscription 

    """
    model = SubscriptionModel(request.session)
    plan_model = PlanModel(request.session)
    customer_model = CustomerModel(request.session)

    company = auth_api_key(request)
    form = validate_form(SubscriptionCreateForm, request)

    customer_guid = form.data['customer_guid']
    plan_guid = form.data['plan_guid']
    amount = form.data.get('amount')
    started_at = form.data.get('started_at')

    customer = customer_model.get(customer_guid)
    if customer.company_guid != company.guid:
        return HTTPForbidden('Can only subscribe to your own customer')
    plan = plan_model.get(plan_guid)
    if plan.company_guid != company.guid:
        return HTTPForbidden('Can only subscribe to your own plan')

    with db_transaction.manager:
        guid = model.create(
            customer_guid=customer_guid, 
            plan_guid=plan_guid, 
            amount=amount, 
            started_at=started_at, 
        )
        model.yield_transactions([guid])
        # TODO: process transactions right away?
    subscription = model.get(guid)
    return subscription


@view_config(route_name='subscription', 
             request_method='GET', 
             renderer='json')
def subscription_get(request):
    """Get and return a subscription 

    """
    company = auth_api_key(request)
    model = SubscriptionModel(request.session)
    guid = request.matchdict['subscription_guid']
    subscription = model.get(guid)
    if subscription is None:
        return HTTPNotFound('No such subscription {}'.format(guid))
    if subscription.customer.company_guid != company.guid:
        return HTTPForbidden('You have no permission to access subscription {}'
                             .format(guid))
    return subscription 
