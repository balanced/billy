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

        # mock balanced customer instance
        mock_balanced_customer = (
            flexmock(id='MOCK_BALANCED_CUSTOMER_ID')
            .should_receive('save')
            .replace_with(lambda: mock_balanced_customer)
            .once()
            .mock()
        )

        class BalancedCustomer(object):
            pass
        flexmock(BalancedCustomer).new_instances(mock_balanced_customer) 

        processor = self.make_one(customer_cls=BalancedCustomer)
        customer_id = processor.create_customer(customer)
        self.assertEqual(customer_id, 'MOCK_BALANCED_CUSTOMER_ID')

    def test_charge(self):
        import balanced

        tx_model = self.transaction_model
        with db_transaction.manager:
            guid = tx_model.create(
                subscription_guid=self.subscription_guid,
                transaction_type=tx_model.TYPE_CHARGE,
                amount=10,
                payment_uri='/v1/credit_card/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )
            transaction = tx_model.get(guid)
            self.customer_model.update(
                guid=transaction.subscription.customer_guid,
                external_id='MOCK_BALANCED_CUSTOMER_ID',
            )
        transaction = tx_model.get(guid)

        # mock result page object of balanced.Debit.query.filter(...)

        def mock_one():
            raise balanced.exc.NoResultFound

        mock_page = (
            flexmock()
            .should_receive('one')
            .replace_with(mock_one)
            .once()
            .mock()
        )

        # mock balanced.Debit.query
        mock_query = (
            flexmock()
            .should_receive('filter')
            .with_args(**{'meta.billy_transaction_guid': transaction.guid})
            .replace_with(lambda **kw: mock_page)
            .mock()
        )

        # mock balanced.Debit class
        class Debit(object): 
            pass
        Debit.query = mock_query

        # mock balanced.Debit instance
        mock_debit = flexmock(id='MOCK_BALANCED_DEBIT_ID')

        # mock balanced.Customer instance
        mock_balanced_customer = (
            flexmock()
            .should_receive('debit')
            .with_args(**{
                'amount': int(transaction.amount * 100),
                'meta.billy_transaction_guid': transaction.guid,
                'source_uri': '/v1/credit_card/tester',
            })
            .replace_with(lambda **kw: mock_debit)
            .once()
            .mock()
        )

        # mock balanced.Customer class
        class BalancedCustomer(object): 
            def find(self, id):
                pass
        (
            flexmock(BalancedCustomer)
            .should_receive('find')
            .with_args('MOCK_BALANCED_CUSTOMER_ID')
            .replace_with(lambda _: mock_balanced_customer)
            .once()
        )

        processor = self.make_one(
            customer_cls=BalancedCustomer, 
            debit_cls=Debit,
        )
        balanced_tx_id = processor.charge(transaction)
        self.assertEqual(balanced_tx_id, 'MOCK_BALANCED_DEBIT_ID')
