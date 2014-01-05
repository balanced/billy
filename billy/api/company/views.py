from __future__ import unicode_literals

import transaction as db_transaction
from pyramid.view import view_config
from pyramid.security import NO_PERMISSION_REQUIRED

from billy.models.company import CompanyModel
from billy.api.utils import validate_form
from billy.api.resources import IndexResource
from billy.api.resources import EntityResource
from billy.api.views import IndexView
from billy.api.views import EntityView
from billy.api.views import api_view_defaults
from .forms import CompanyCreateForm


class CompanyResource(EntityResource):
    @property
    def company(self):
        return self.entity


class CompanyIndexResource(IndexResource):
    MODEL_CLS = CompanyModel
    ENTITY_NAME = 'company'
    ENTITY_RESOURCE = CompanyResource


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
    pass
