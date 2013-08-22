from __future__ import unicode_literals

import transaction as db_transaction
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPNotFound
from pyramid.httpexceptions import HTTPForbidden

from billy.models.customer import CustomerModel 
from billy.models.plan import PlanModel
from billy.models.subscription import SubscriptionModel 
from billy.api.auth import auth_api_key


@view_config(route_name='subscription_list', 
             request_method='POST', 
             renderer='json')
def subscription_list_post(request):
    """Create a new subscription 

    """
    company = auth_api_key(request)
    model = SubscriptionModel(request.session)
    plan_model = PlanModel(request.session)
    customer_model = CustomerModel(request.session)
    # TODO: do validation here
    customer_guid = request.params['customer_guid']
    plan_guid = request.params['plan_guid']
    amount = request.params.get('amount')

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
    model = SubscriptionModel(request.session)
    guid = request.matchdict['subscription_guid']
    subscription = model.get(guid)
    if subscription is None:
        return HTTPNotFound('No such subscription {}'.format(guid))
    if subscription.customer.company_guid != company.guid:
        return HTTPForbidden('You have no permission to access subscription {}'
                             .format(guid))
    return subscription 
