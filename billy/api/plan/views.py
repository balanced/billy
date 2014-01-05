from __future__ import unicode_literals

import transaction as db_transaction
from pyramid.view import view_config
from pyramid.view import view_defaults
from pyramid.security import Allow
from pyramid.security import Authenticated
from pyramid.security import authenticated_userid
from pyramid.httpexceptions import HTTPNotFound
from pyramid.httpexceptions import HTTPForbidden
from pyramid.httpexceptions import HTTPBadRequest

from billy.models.plan import PlanModel 
from billy.models.customer import CustomerModel 
from billy.models.subscription import SubscriptionModel 
from billy.models.transaction import TransactionModel 
from billy.api.utils import validate_form
from billy.api.utils import list_by_context
from .forms import PlanCreateForm


class PlanIndexResource(object):
    __acl__ = [
        #       principal      action
        (Allow, Authenticated, 'view'),
        (Allow, Authenticated, 'create'),
    ]

    def __init__(self, request):
        self.request = request

    def __getitem__(self, key):
        model = self.request.model_factory.create_plan_model()
        plan = model.get(key)
        if plan is None:
            raise HTTPNotFound('No such plan {}'.format(key))
        return PlanResource(plan)


class PlanResource(object):
    def __init__(self, plan):
        self.plan = plan
        # make sure only the owner company can access the plan
        company_principal = 'company:{}'.format(self.plan.company.guid)
        self.__acl__ = [
            #       principal          action
            (Allow, company_principal, 'view'),
        ]


@view_defaults(
    route_name='plan_index', 
    context=PlanIndexResource, 
    renderer='json',
)
class PlanIndexView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    @view_config(request_method='GET', permission='view')
    def get(self):
        request = self.request
        company = authenticated_userid(request)
        return list_by_context(request, PlanModel, company)

    @view_config(request_method='POST', permission='create')
    def post(self):
        request = self.request
        company = authenticated_userid(request)
        form = validate_form(PlanCreateForm, request)
        
        plan_type = form.data['plan_type']
        amount = form.data['amount']
        frequency = form.data['frequency']
        interval = form.data['interval']
        if interval is None:
            interval = 1

        # TODO: make sure user cannot create a post to a deleted company

        model = request.model_factory.create_plan_model()
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
            plan = model.create(
                company=company, 
                plan_type=plan_type,
                amount=amount, 
                frequency=frequency, 
                interval=interval, 
            )
        return plan 


@view_defaults(
    route_name='plan_index', 
    context=PlanResource, 
    renderer='json',
)
class PlanView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    @view_config(request_method='GET')
    def get(self):
        return self.context.plan

    @view_config(request_method='DELETE')
    def delete(self):
        model = self.request.model_factory.create_plan_model()
        plan = self.context.plan
        if plan.deleted:
            return HTTPBadRequest('Plan {} was already deleted'.format(plan.guid))
        with db_transaction.manager:
            model.delete(plan)
        return plan 

    @view_config(name='customers')
    def customer_index(self):
        """Get and return the list of customers unrder current plan

        """
        return list_by_context(self.request, CustomerModel, self.context.plan)

    @view_config(name='subscriptions')
    def subscription_index(self):
        """Get and return the list of subscriptions unrder current plan

        """
        return list_by_context(self.request, SubscriptionModel, self.context.plan)

    @view_config(name='transactions')
    def transaction_index(self):
        """Get and return the list of transactions unrder current plan

        """
        return list_by_context(self.request, TransactionModel, self.context.plan)


def plan_index_root(request):
    return PlanIndexResource(request)
