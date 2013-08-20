from __future__ import unicode_literals
import unittest
import datetime

import transaction as db_transaction
from flexmock import flexmock
from freezegun import freeze_time

from billy.tests.helper import ModelTestCase


class TestPaymentProcessorModel(unittest.TestCase):

    def test_base_processor(self):
        from billy.models.processors.base import PaymentProcessor
        processor = PaymentProcessor()
        with self.assertRaises(NotImplementedError):
            processor.create_customer(None)
        with self.assertRaises(NotImplementedError):
            processor.prepare_customer(None)
        with self.assertRaises(NotImplementedError):
            processor.charge(None)
        with self.assertRaises(NotImplementedError):
            processor.payout(None)


@freeze_time('2013-08-16')
class TestBalancedProcessorModel(ModelTestCase):

    def setUp(self):
        from billy.models.company import CompanyModel
        from billy.models.customer import CustomerModel
        from billy.models.plan import PlanModel
        from billy.models.subscription import SubscriptionModel
        from billy.models.transaction import TransactionModel
        super(TestBalancedProcessorModel, self).setUp()
        # build the basic scenario for transaction model
        self.company_model = CompanyModel(self.session)
        self.customer_model = CustomerModel(self.session)
        self.plan_model = PlanModel(self.session)
        self.subscription_model = SubscriptionModel(self.session)
        self.transaction_model = TransactionModel(self.session)
        with db_transaction.manager:
            self.company_guid = self.company_model.create('my_secret_key')
            self.plan_guid = self.plan_model.create(
                company_guid=self.company_guid,
                plan_type=self.plan_model.TYPE_CHARGE,
                amount=10,
                frequency=self.plan_model.FREQ_MONTHLY,
            )
            self.customer_guid = self.customer_model.create(
                company_guid=self.company_guid,
            )
            self.subscription_guid = self.subscription_model.create(
                customer_guid=self.customer_guid,
                plan_guid=self.plan_guid,
                payment_uri='/v1/credit_card/tester',
            )

    def make_one(self, *args, **kwargs):
        from billy.models.processors.balanced_payments import BalancedProcessor
        return BalancedProcessor(*args, **kwargs)

    def test_create_customer(self):
        customer = self.customer_model.get(self.customer_guid)

        mock_balanced_customer = (
            flexmock(id='MOCK_BALANCED_CUSTOMER_ID')
            .should_receive('save')
            .replace_with(lambda: mock_balanced_customer)
            .once()
            .mock()
        )

        class BalancedCustomer(object): pass
        flexmock(BalancedCustomer).new_instances(mock_balanced_customer)
    
        processor = self.make_one(customer_cls=BalancedCustomer)
        customer_id = processor.create_customer(customer)
        self.assertEqual(customer_id, 'MOCK_BALANCED_CUSTOMER_ID')
