from __future__ import unicode_literals

import transaction as db_transaction
from pyramid.view import view_config
from pyramid.security import authenticated_userid
from pyramid.httpexceptions import HTTPBadRequest

from billy.models.plan import PlanModel
from billy.models.customer import CustomerModel
from billy.models.subscription import SubscriptionModel
from billy.models.transaction import TransactionModel
from billy.models.invoice import InvoiceModel
from billy.api.utils import validate_form
from billy.api.utils import list_by_context
from billy.api.resources import IndexResource
from billy.api.resources import EntityResource
from billy.api.views import IndexView
from billy.api.views import EntityView
from billy.api.views import api_view_defaults
from .forms import PlanCreateForm


class PlanResource(EntityResource):
    @property
    def company(self):
        return self.entity.company


class PlanIndexResource(IndexResource):
    MODEL_CLS = PlanModel
    ENTITY_NAME = 'plan'
    ENTITY_RESOURCE = PlanResource


@api_view_defaults(context=PlanIndexResource)
class PlanIndexView(IndexView):

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
        with db_transaction.manager:
            plan = model.create(
                company=company,
                plan_type=plan_type,
                amount=amount,
                frequency=frequency,
                interval=interval,
            )
        return plan


@api_view_defaults(context=PlanResource)
class PlanView(EntityView):

    @view_config(request_method='GET')
    def get(self):
        return self.context.entity

    @view_config(request_method='DELETE')
    def delete(self):
        model = self.request.model_factory.create_plan_model()
        plan = self.context.entity
        if plan.deleted:
            return HTTPBadRequest('Plan {} was already deleted'.format(plan.guid))
        with db_transaction.manager:
            model.delete(plan)
        return plan

    @view_config(name='customers')
    def customer_index(self):
        """Get and return the list of customers unrder current plan

        """
        return list_by_context(self.request, CustomerModel, self.context.entity)

    @view_config(name='subscriptions')
    def subscription_index(self):
        """Get and return the list of subscriptions unrder current plan

        """
        return list_by_context(self.request, SubscriptionModel, self.context.entity)

    @view_config(name='invoices')
    def invoice_index(self):
        """Get and return the list of invoices unrder current plan

        """
        return list_by_context(self.request, InvoiceModel, self.context.entity)

    @view_config(name='transactions')
    def transaction_index(self):
        """Get and return the list of transactions unrder current plan

        """
        return list_by_context(self.request, TransactionModel, self.context.entity)
