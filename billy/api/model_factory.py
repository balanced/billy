from __future__ import unicode_literals

from billy.models.company import CompanyModel
from billy.models.customer import CustomerModel
from billy.models.plan import PlanModel
from billy.models.invoice import InvoiceModel
from billy.models.subscription import SubscriptionModel
from billy.models.transaction import TransactionModel


class ModelFactory(object):
    """This object reads configurations from request and creates data models

    """

    def __init__(self, request):
        self.request = request

    def create_company_model(self):
        """Create a company model

        """
        return CompanyModel(self.request.session)

    def create_customer_model(self):
        """Create a customer model

        """
        return CustomerModel(self.request.session)

    def create_plan_model(self):
        """Create a plan model

        """
        return PlanModel(self.request.session)

    def create_invoice_model(self):
        """Create an invoice model

        """
        return InvoiceModel(self.request.session)

    def create_subscription_model(self):
        """Create a subscription model

        """
        return SubscriptionModel(self.request.session)

    def create_transaction_model(self):
        """Create a transaction model

        """
        maximum_retry = int(self.request.registry.settings.get(
            'billy.transaction.maximum_retry', 
            TransactionModel.DEFAULT_MAXIMUM_RETRY,
        ))
        return TransactionModel(
            self.request.session, 
            maximum_retry=maximum_retry,
        )
