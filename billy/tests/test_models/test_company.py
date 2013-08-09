from __future__ import unicode_literals
from datetime import datetime

from models import Company, ProcessorType
from models.processor import DummyProcessor
from tests import BaseTestCase, fixtures


class InvoiceScenarioTest(BaseTestCase):
    def setUp(self):
        super(InvoiceScenarioTest, self).setUp()
        # Prune old companies
        self.company = self.test_companies[0]


    def basic_test(self):
        # Create a company
        company = Company.create(
            processor_type=ProcessorType.DUMMY, # Dummy processor,
            processor_credential="API_KEY_WITH_PROCESSOR",
            is_test=True, # Allows us to delete it!
        )

        # Primary functionality
        company.create_coupon(**fixtures.sample_coupon())
        company.create_customer(**fixtures.sample_customer())
        company.create_charge_plan(**fixtures.sample_plan())
        company.create_payout_plan(**fixtures.sample_payout())


        # Retrieving the instantiated processor class
        processor_class = company.processor
        self.assertIsInstance(processor_class, DummyProcessor)

        # Performing transactions, generally though these should be preferred
        # by some application logic.
        processor_class.check_balance('SOME_CUSTOMER_ID')











