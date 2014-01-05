from __future__ import unicode_literals

import transaction as db_transaction
from pyramid.view import view_config
from pyramid.security import authenticated_userid
from pyramid.httpexceptions import HTTPBadRequest

from billy.models.customer import CustomerModel
from billy.models.invoice import InvoiceModel
from billy.models.subscription import SubscriptionModel
from billy.models.transaction import TransactionModel
from billy.api.utils import validate_form
from billy.api.utils import list_by_context
from billy.api.resources import IndexResource
from billy.api.resources import EntityResource
from billy.api.views import IndexView
from billy.api.views import EntityView
from billy.api.views import api_view_defaults
from .forms import CustomerCreateForm


class CustomerResource(EntityResource):
    @property
    def company(self):
        return self.entity.company


class CustomerIndexResource(IndexResource):
    MODEL_CLS = CustomerModel
    ENTITY_NAME = 'customer'
    ENTITY_RESOURCE = CustomerResource


@api_view_defaults(context=CustomerIndexResource)
class CustomerIndexView(IndexView):

    @view_config(request_method='GET', permission='view')
    def get(self):
        request = self.request
        company = authenticated_userid(request)
        return list_by_context(request, CustomerModel, company)

    @view_config(request_method='POST', permission='create')
    def post(self):
        request = self.request
        company = authenticated_userid(request)
        form = validate_form(CustomerCreateForm, request)
        
        processor_uri = form.data.get('processor_uri')

        # TODO: make sure user cannot create a customer to a deleted company

        model = request.model_factory.create_customer_model()
        with db_transaction.manager:
            customer = model.create(
                processor_uri=processor_uri,
                company=company, 
            )
        return customer


@api_view_defaults(context=CustomerResource)
class CustomerView(EntityView):

    @view_config(request_method='GET')
    def get(self):
        return self.context.entity

    @view_config(request_method='DELETE')
    def delete(self):
        model = self.request.model_factory.create_customer_model()
        customer = self.context.entity
        if customer.deleted:
            return HTTPBadRequest('Customer {} was already deleted'
                                  .format(customer.guid))
        with db_transaction.manager:
            model.delete(customer)
        return customer

    @view_config(name='invoices')
    def invoice_index(self):
        """Get and return the list of invoices unrder current customer

        """
        customer = self.context.entity
        return list_by_context(self.request, InvoiceModel, customer)

    @view_config(name='subscriptions')
    def subscription_index(self):
        """Get and return the list of subscriptions unrder current customer

        """
        customer = self.context.entity
        return list_by_context(self.request, SubscriptionModel, customer)

    @view_config(name='transactions')
    def transaction_index(self):
        """Get and return the list of transactions unrder current customer

        """
        customer = self.context.entity
        return list_by_context(self.request, TransactionModel, customer)
