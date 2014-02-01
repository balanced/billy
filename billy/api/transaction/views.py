from __future__ import unicode_literals

from pyramid.view import view_config
from pyramid.security import authenticated_userid

from billy.models.invoice import InvoiceModel
from billy.models.transaction import TransactionModel
from billy.api.utils import list_by_context
from billy.api.resources import IndexResource
from billy.api.resources import EntityResource
from billy.api.views import IndexView
from billy.api.views import EntityView
from billy.api.views import api_view_defaults


class TransactionResource(EntityResource):
    @property
    def company(self):
        # make sure only the owner company can access the customer
        if self.entity.invoice.invoice_type == InvoiceModel.types.SUBSCRIPTION:
            company = self.entity.invoice.subscription.plan.company
        else:
            company = self.entity.invoice.customer.company
        return company


class TransactionIndexResource(IndexResource):
    MODEL_CLS = TransactionModel
    ENTITY_NAME = 'transaction'
    ENTITY_RESOURCE = TransactionResource


@api_view_defaults(context=TransactionIndexResource)
class TransactionIndexView(IndexView):

    @view_config(request_method='GET', permission='view')
    def get(self):
        request = self.request
        company = authenticated_userid(request)
        return list_by_context(request, TransactionModel, company)


@api_view_defaults(context=TransactionResource)
class TransactionView(EntityView):

    @view_config(request_method='GET')
    def get(self):
        return self.context.entity
