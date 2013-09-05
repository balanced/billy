from __future__ import unicode_literals

import transaction as db_transaction
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPNotFound
from pyramid.httpexceptions import HTTPForbidden

from billy.models.plan import PlanModel 
from billy.api.auth import auth_api_key
from billy.api.utils import validate_form
from .forms import PlanCreateForm


@view_config(route_name='plan_list', 
             request_method='POST', 
             renderer='json')
def plan_list_post(request):
    """Create a new plan 

    """
    company = auth_api_key(request)
    form = validate_form(PlanCreateForm, request)
    
    plan_type = form.data['plan_type']
    amount = form.data['amount']
    frequency = form.data['frequency']
    interval = form.data['interval']
    if interval is None:
        interval = 1
    company_guid = company.guid

    model = PlanModel(request.session)
    type_map = dict(
        charge=model.TYPE_CHARGE,
        payout=model.TYPE_PAYOUT,
    )
    plan_type = type_map[plan_type]
    freq_map = dict(
        daily=model.FREQ_DAILY,
        weekly=model.FREQ_WEEKLY,
        monthly=model.FREQ_MONTHLY,
        yearly=model.FREQ_YEARLY,
    )
    frequency = freq_map[frequency]

    with db_transaction.manager:
        guid = model.create(
            company_guid=company_guid, 
            plan_type=plan_type,
            amount=amount, 
            frequency=frequency, 
            interval=interval, 
        )
    plan = model.get(guid)
    return plan 


@view_config(route_name='plan', 
             request_method='GET', 
             renderer='json')
def plan_get(request):
    """Get and return a plan 

    """
    company = auth_api_key(request)
    model = PlanModel(request.session)
    guid = request.matchdict['plan_guid']
    plan = model.get(guid)
    if plan is None:
        return HTTPNotFound('No such plan {}'.format(guid))
    if plan.company_guid != company.guid:
        return HTTPForbidden('You have no permission to access plan {}'
                             .format(guid))
    return plan 
