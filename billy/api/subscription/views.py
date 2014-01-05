from __future__ import unicode_literals

import transaction as db_transaction
from pyramid.view import view_config
from pyramid.settings import asbool
from pyramid.security import authenticated_userid
from pyramid.httpexceptions import HTTPForbidden
from pyramid.httpexceptions import HTTPBadRequest

from billy.models.subscription import SubscriptionModel
from billy.models.transaction import TransactionModel
from billy.api.utils import validate_form
from billy.api.utils import form_errors_to_bad_request
from billy.api.utils import list_by_context
from billy.api.resources import IndexResource
from billy.api.resources import EntityResource
from billy.api.views import IndexView
from billy.api.views import EntityView
from billy.api.views import api_view_defaults
from .forms import SubscriptionCreateForm
from .forms import SubscriptionCancelForm


class SubscriptionResource(EntityResource):
    @property
    def company(self):
        return self.entity.plan.company


class SubscriptionIndexResource(IndexResource):
    MODEL_CLS = SubscriptionModel
    ENTITY_NAME = 'subscription'
    ENTITY_RESOURCE = SubscriptionResource


@api_view_defaults(context=SubscriptionIndexResource)
class SubscriptionIndexView(IndexView):

    @view_config(request_method='GET', permission='view')
    def get(self):
        request = self.request
        company = authenticated_userid(request)
        return list_by_context(request, SubscriptionModel, company)

    @view_config(request_method='POST', permission='create')
    def post(self):
        request = self.request
        company = authenticated_userid(request)

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


@api_view_defaults(context=SubscriptionResource)
class SubscriptionView(EntityView):

    @view_config(request_method='GET')
    def get(self):
        return self.context.entity

    @view_config(name='cancel', request_method='POST')
    def cancel(self):
        # TODO: it appears a DELETE request with body is not a good idea
        # for HTTP protocol as many server doesn't support this, this is why
        # we use another view with post method, maybe we should use a better 
        # approach later
        request = self.request
        subscription = self.context.entity
        form = validate_form(SubscriptionCancelForm, request)

        prorated_refund = asbool(form.data.get('prorated_refund', False))
        refund_amount = form.data.get('refund_amount')
        appears_on_statement_as = form.data.get('appears_on_statement_as')
        if not appears_on_statement_as:
            appears_on_statement_as = None

        sub_model = request.model_factory.create_subscription_model()
        tx_model = request.model_factory.create_transaction_model()

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

    @view_config(name='transactions')
    def transaction_index(self):
        """Get and return the list of transactions unrder current customer

        """
        return list_by_context(self.request, TransactionModel, self.context.entity)
