from __future__ import unicode_literals

import transaction as db_transaction
from pyramid.view import view_config
from pyramid.security import NO_PERMISSION_REQUIRED
from pyramid.security import Allow
from pyramid.security import Everyone

from billy.models.company import CompanyModel
from billy.api.utils import validate_form
from billy.api.resources import BaseResource
from billy.api.resources import URLMapResource
from billy.api.resources import IndexResource
from billy.api.resources import EntityResource
from billy.api.views import BaseView
from billy.api.views import IndexView
from billy.api.views import EntityView
from billy.api.views import api_view_defaults
from .forms import CompanyCreateForm


class CompanyResource(EntityResource):
    @property
    def company(self):
        return self.entity

    def __getitem__(self, item):
        if item == 'callbacks':
            return CallbackIndex(self.company, self.request, self)


class CompanyIndexResource(IndexResource):
    MODEL_CLS = CompanyModel
    ENTITY_NAME = 'company'
    ENTITY_RESOURCE = CompanyResource


# TODO: this is little bit verbose, maybe we can find a better way later
class CallbackIndex(URLMapResource):
    """Callback index is the resource at /v1/companies/<guid>/callbacks

    """
    __name__ = 'callbacks'

    def __init__(self, company, request, parent=None):
        self.company = company
        url_map = {company.callback_key: Callback(company, request, parent)}
        super(CallbackIndex, self).__init__(request, url_map, parent, self.__name__)


class Callback(BaseResource):
    __acl__ = [
        # We need to make it easy for payment processor to callback without
        # authentication information. The `callback_key` in URL is like a
        # secret key itself. So just open it up to public

        #       principal, action
        (Allow, Everyone, 'callback'),
    ]

    def __init__(self, company, request, parent=None):
        self.company = company
        super(Callback, self).__init__(request, parent, company.callback_key)


@api_view_defaults(context=CompanyIndexResource)
class CompanyIndexView(IndexView):

    @view_config(request_method='POST', permission=NO_PERMISSION_REQUIRED)
    def post(self):
        request = self.request
        form = validate_form(CompanyCreateForm, request)
        processor_key = form.data['processor_key']
        # TODO: validate API key in processor?

        model = request.model_factory.create_company_model()
        with db_transaction.manager:
            company = model.create(processor_key=processor_key)
        return company


@api_view_defaults(context=CompanyResource)
class CompanyView(EntityView):

    @view_config(request_method='GET')
    def get(self):
        return self.context.entity


@api_view_defaults(context=Callback, permission='callback')
class CallbackView(BaseView):

    @view_config(request_method='POST')
    def post(self):
        processor = self.request.model_factory.create_processor()
        processor.callback(self.context.company, self.request.json)
        return dict(code='ok')
