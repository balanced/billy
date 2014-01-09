from __future__ import unicode_literals

from billy.models.company import CompanyModel
from billy.models.customer import CustomerModel
from billy.models.plan import PlanModel
from billy.models.invoice import InvoiceModel
from billy.models.subscription import SubscriptionModel
from billy.models.transaction import TransactionModel
from billy.models.transaction_failure import TransactionFailureModel


class ModelFactory(object):

    def __init__(self, session, settings=None, processor_factory=None):
        self.session = session
        self.settings = settings or {}
        self.processor_factory = processor_factory

    def create_processor(self):
        """Create a processor

        """
        return self.processor_factory()

    def create_company_model(self):
        """Create a company model

        """
        return CompanyModel(self)

    def create_customer_model(self):
        """Create a customer model

        """
        return CustomerModel(self)

    def create_plan_model(self):
        """Create a plan model

        """
        return PlanModel(self)

    def create_invoice_model(self):
        """Create an invoice model

        """
        return InvoiceModel(self)

    def create_subscription_model(self):
        """Create a subscription model

        """
        return SubscriptionModel(self)

    def create_transaction_model(self):
        """Create a transaction model

        """
        return TransactionModel(self)

    def create_transaction_failure_model(self):
        """Create a transaction failure model

        """
        return TransactionFailureModel(self)
