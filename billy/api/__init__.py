from __future__ import unicode_literals

from .company.views import CompanyIndexResource
from .customer.views import CustomerIndexResource
from .invoice.views import InvoiceIndexResource
from .plan.views import PlanIndexResource
from .subscription.views import SubscriptionIndexResource
from .transaction.views import TransactionIndexResource


class APIRev1Resource(object):
    def __init__(self, request, parent=None, name=None):
        self.__parent__ = parent
        self.__name__ = name
        self.request = request
        # map url prefix to resources
        self.url_map = dict(
            companies=CompanyIndexResource,
            customers=CustomerIndexResource,
            invoices=InvoiceIndexResource,
            plans=PlanIndexResource,
            subscriptions=SubscriptionIndexResource,
            transactions=TransactionIndexResource,
        )

    def __getitem__(self, key):
        cls = self.url_map.get(key)
        if cls is not None:
            return cls(self.request, parent=self, name=key)
        return None


class RootResource(object):
    __name__ = ''

    def __init__(self, request):
        self.request = request

    def __getitem__(self, key):
        if key == 'v1':
            return APIRev1Resource(self.request, parent=self, name=key)
        return None


def includeme(config):
    config.add_route('server_info', '/')
    config.set_root_factory(RootResource)
