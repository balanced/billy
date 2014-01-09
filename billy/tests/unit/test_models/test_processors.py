from __future__ import unicode_literals
import unittest

import mock
import balanced
import transaction as db_transaction
from freezegun import freeze_time

from billy.models.processors.base import PaymentProcessor
from billy.models.processors.balanced_payments import InvalidURIFormat
from billy.tests.unit.helper import ModelTestCase


class TestPaymentProcessorModel(unittest.TestCase):

    def test_base_processor(self):
        processor = PaymentProcessor()
        with self.assertRaises(NotImplementedError):
            processor.validate_customer(None)
        with self.assertRaises(NotImplementedError):
            processor.create_customer(None)
        with self.assertRaises(NotImplementedError):
            processor.prepare_customer(None)
        with self.assertRaises(NotImplementedError):
            processor.charge(None)
        with self.assertRaises(NotImplementedError):
            processor.payout(None)
        with self.assertRaises(NotImplementedError):
            processor.refund(None)


@freeze_time('2013-08-16')
class TestBalancedProcessorModel(ModelTestCase):

    def setUp(self):
        super(TestBalancedProcessorModel, self).setUp()
        # build the basic scenario for transaction model
        with db_transaction.manager:
            self.company = self.company_model.create('my_secret_key')
            self.plan = self.plan_model.create(
                company=self.company,
                plan_type=self.plan_model.TYPE_CHARGE,
                amount=10,
                frequency=self.plan_model.FREQ_MONTHLY,
            )
            self.customer = self.customer_model.create(
                company=self.company,
                processor_uri='MOCK_BALANCED_CUSTOMER_URI',
            )
            self.subscription = self.subscription_model.create(
                customer=self.customer,
                plan=self.plan,
                funding_instrument_uri='/v1/credit_card/tester',
            )
            self.invoice = self.invoice_model.create(
                customer=self.customer,
                amount=100,
            )

    def make_one(self, *args, **kwargs):
        from billy.models.processors.balanced_payments import BalancedProcessor
        return BalancedProcessor(*args, **kwargs)

    def test_validate_customer(self):
        # mock class
        BalancedCustomer = mock.Mock()
        BalancedCustomer.find.return_value = mock.Mock(uri='MOCK_CUSTOMER_URI')

        processor = self.make_one(customer_cls=BalancedCustomer)
        result = processor.validate_customer('/v1/customers/xxx')
        self.assertTrue(result)

        BalancedCustomer.find.assert_called_once_with('/v1/customers/xxx')

    def test_validate_customer_with_invalid_uri(self):
        processor = self.make_one()
        with self.assertRaises(InvalidURIFormat):
            processor.validate_customer('CUXXXXXXXX')

    @mock.patch('balanced.configure')
    def test_create_customer(self, configure_method):
        self.customer.processor_uri = None

        # mock instance
        balanced_customer = mock.Mock()
        balanced_customer.save.return_value = mock.Mock(uri='MOCK_CUSTOMER_URI')
        # mock class
        BalancedCustomer = mock.Mock()
        BalancedCustomer.return_value = balanced_customer

        processor = self.make_one(customer_cls=BalancedCustomer)
        customer_id = processor.create_customer(self.customer)
        self.assertEqual(customer_id, 'MOCK_CUSTOMER_URI')

        # make sure API key is set correctly
        configure_method.assert_called_once_with('my_secret_key')
        # make sure the customer is created correctly
        BalancedCustomer.assert_called_once_with(**{
            'meta.billy_customer_guid': self.customer.guid,
        })
        balanced_customer.save.assert_called_once_with()

    @mock.patch('balanced.configure')
    def test_prepare_customer_with_card(self, configure_method):
        # mock instance
        balanced_customer = mock.Mock()
        # mock class
        BalancedCustomer = mock.Mock()
        BalancedCustomer.find.return_value = balanced_customer

        processor = self.make_one(customer_cls=BalancedCustomer)
        processor.prepare_customer(self.customer, '/v1/cards/my_card')
        # make sure API key is set correctly
        configure_method.assert_called_once_with('my_secret_key')
        # make sure the customer find method is called
        BalancedCustomer.find.assert_called_once_with(self.customer.processor_uri)
        # make sure card is added correctly
        balanced_customer.add_card.assert_called_once_with('/v1/cards/my_card')

    @mock.patch('balanced.configure')
    def test_prepare_customer_with_bank_account(self, configure_method):
        # mock instance
        balanced_customer = mock.Mock()
        # mock class
        BalancedCustomer = mock.Mock()
        BalancedCustomer.find.return_value = balanced_customer

        processor = self.make_one(customer_cls=BalancedCustomer)
        processor.prepare_customer(
            self.customer, 
            '/v1/bank_accounts/my_account'
        )
        # make sure API key is set correctly
        configure_method.assert_called_once_with('my_secret_key')
        # make sure the customer find method is called
        BalancedCustomer.find.assert_called_once_with(self.customer.processor_uri)
        # make sure card is added correctly
        balanced_customer.add_bank_account.assert_called_once_with(
            '/v1/bank_accounts/my_account',
        )

    def test_prepare_customer_with_none_funding_instrument_uri(self):
        # mock instance
        balanced_customer = mock.Mock()
        # mock class
        BalancedCustomer = mock.Mock()
        BalancedCustomer.find.return_value = balanced_customer

        processor = self.make_one(customer_cls=BalancedCustomer)
        processor.prepare_customer(self.customer, None)

        # make sure add_card and add_bank_account will not be called
        self.assertFalse(balanced_customer.add_card.called, 0)
        self.assertFalse(balanced_customer.add_bank_account.called, 0)

    def test_prepare_customer_with_bad_funding_instrument_uri(self):
        # mock instance
        balanced_customer = mock.Mock()
        # mock class
        BalancedCustomer = mock.Mock()
        BalancedCustomer.find.return_value = balanced_customer

        processor = self.make_one(customer_cls=BalancedCustomer)
        with self.assertRaises(ValueError):
            processor.prepare_customer(self.customer, '/v1/bitcoin/12345')

    @mock.patch('balanced.configure')
    def _test_operation(
        self, 
        configure_method,
        cls_name, 
        processor_method_name, 
        api_method_name,
        extra_api_kwargs,
    ):
        tx_model = self.transaction_model
        with db_transaction.manager:
            transaction = tx_model.create(
                invoice=self.invoice,
                transaction_type=tx_model.TYPE_CHARGE,
                amount=10,
                funding_instrument_uri='/v1/credit_card/tester',
                appears_on_statement_as='hello baby',
            )
            self.customer_model.update(
                customer=self.customer,
                processor_uri='MOCK_BALANCED_CUSTOMER_URI',
            )

        # mock page
        page = mock.Mock()
        page.one.side_effect = balanced.exc.NoResultFound
        # mock resource
        resource = mock.Mock(uri='MOCK_BALANCED_RESOURCE_URI')
        # mock customer instance
        balanced_customer = mock.Mock()
        api_method = getattr(balanced_customer, api_method_name)
        api_method.return_value = resource
        api_method.__name__ = api_method_name
        # mock customer class
        BalancedCustomer = mock.Mock()
        BalancedCustomer.find.return_value = balanced_customer
        # mock resource class
        Resource = mock.Mock()
        Resource.query.filter.return_value = page

        processor = self.make_one(
            customer_cls=BalancedCustomer, 
            **{cls_name: Resource}
        )
        method = getattr(processor, processor_method_name)
        balanced_tx_id = method(transaction)
        self.assertEqual(balanced_tx_id, 'MOCK_BALANCED_RESOURCE_URI')
        # make sure the customer find method is called
        BalancedCustomer.find.assert_called_once_with(self.customer.processor_uri)
        # make sure API key is set correctly
        configure_method.assert_called_once_with('my_secret_key')
        # make sure query is made correctly
        expected_kwargs = {'meta.billy.transaction_guid': transaction.guid}
        Resource.query.filter.assert_called_once_with(**expected_kwargs)
        # make sure the operation method is called properly
        expected_kwargs = dict(
            amount=transaction.amount,
            meta={'billy.transaction_guid': transaction.guid},
            description=(
                'Generated by Billy from invoice {}'.format(self.invoice.guid)
            ),
            appears_on_statement_as='hello baby',
        )
        expected_kwargs.update(extra_api_kwargs)
        api_method = getattr(balanced_customer, api_method_name)
        api_method.assert_called_once_with(**expected_kwargs)

    def _test_operation_with_created_record(
        self, 
        cls_name, 
        processor_method_name,
        api_method_name,
    ):
        tx_model = self.transaction_model
        with db_transaction.manager:
            transaction = tx_model.create(
                invoice=self.invoice,
                transaction_type=tx_model.TYPE_CHARGE,
                amount=10,
                funding_instrument_uri='/v1/credit_card/tester',
            )

        # mock resource
        resource = mock.Mock(uri='MOCK_BALANCED_RESOURCE_URI')
        # mock page
        page = mock.Mock()
        page.one.return_value = resource
        # mock customer instance
        customer = mock.Mock()
        api_method = getattr(customer, api_method_name)
        api_method.return_value = resource
        api_method.__name__ = api_method_name
        # mock customer class
        Customer = mock.Mock()
        Customer.find.return_value = customer 
        # mock resource class
        Resource = mock.Mock()
        Resource.query.filter.return_value = page

        processor = self.make_one(
            customer_cls=Customer, 
            **{cls_name: Resource}
        )
        method = getattr(processor, processor_method_name)
        balanced_res_uri = method(transaction)
        self.assertEqual(balanced_res_uri, 'MOCK_BALANCED_RESOURCE_URI')

        # make sure the api method is not called
        self.assertFalse(Customer.find.called)
        self.assertFalse(api_method.called)
        # make sure query is made correctly
        expected_kwargs = {'meta.billy.transaction_guid': transaction.guid}
        Resource.query.filter.assert_called_once_with(**expected_kwargs)

    def test_charge(self):
        self._test_operation(
            cls_name='debit_cls', 
            processor_method_name='charge',
            api_method_name='debit',
            extra_api_kwargs=dict(source_uri='/v1/credit_card/tester'),
        )

    def test_charge_with_created_record(self):
        self._test_operation_with_created_record(
            cls_name='debit_cls',
            processor_method_name='charge',
            api_method_name='debit',
        )

    def test_payout(self):
        self._test_operation(
            cls_name='credit_cls', 
            processor_method_name='payout',
            api_method_name='credit',
            extra_api_kwargs=dict(destination_uri='/v1/credit_card/tester'),
        )

    def test_payout_with_created_record(self):
        self._test_operation_with_created_record(
            cls_name='credit_cls',
            processor_method_name='payout',
            api_method_name='credit',
        )

    def _create_refund_transaction(self):
        tx_model = self.transaction_model
        with db_transaction.manager:
            charge_transaction = tx_model.create(
                invoice=self.invoice,
                transaction_type=tx_model.TYPE_CHARGE,
                amount=100,
                funding_instrument_uri='/v1/credit_card/tester',
            )
            charge_transaction.status = tx_model.STATUS_DONE
            charge_transaction.processor_uri = 'MOCK_BALANCED_DEBIT_URI'
            self.session.flush()

            transaction = tx_model.create(
                invoice=self.invoice,
                transaction_type=tx_model.TYPE_REFUND,
                reference_to=charge_transaction,
                amount=56,
                appears_on_statement_as='hello baby',
            )
        return transaction

    def test_refund(self):
        transaction = self._create_refund_transaction()

        # mock page
        page = mock.Mock()
        page.one.side_effect = balanced.exc.NoResultFound
        # mock debit instance
        debit = mock.Mock()
        debit.refund.return_value = mock.Mock(uri='MOCK_REFUND_URI')
        debit.refund.__name__ = 'refund'
        # mock customer class
        Customer = mock.Mock()
        Customer.find.return_value = mock.Mock()
        # mock refund class
        Refund = mock.Mock()
        Refund.query.filter.return_value = page
        # mock debit class
        Debit = mock.Mock()
        Debit.find.return_value = debit

        processor = self.make_one(
            refund_cls=Refund,
            debit_cls=Debit,
            customer_cls=Customer,
        )
        refund_uri = processor.refund(transaction)
        self.assertEqual(refund_uri, 'MOCK_REFUND_URI')

        Debit.find.assert_called_once_with(transaction.reference_to.processor_uri)
        description = (
            'Generated by Billy from invoice {}'
            .format(self.invoice.guid)
        )
        expected_kwargs = dict(
            amount=transaction.amount,
            meta={'billy.transaction_guid': transaction.guid},
            description=description,
            appears_on_statement_as='hello baby',
        )
        debit.refund.assert_called_once_with(**expected_kwargs)

    def test_refund_with_created_record(self):
        transaction = self._create_refund_transaction()

        # mock resource
        resource = mock.Mock(uri='MOCK_BALANCED_REFUND_URI')
        # mock page
        page = mock.Mock()
        page.one.return_value = resource
        # mock debit instance
        debit = mock.Mock()
        debit.refund.return_value = mock.Mock(uri='MOCK_REFUND_URI')
        debit.refund.__name__ = 'refund'
        # mock customer class
        Customer = mock.Mock()
        Customer.find.return_value = mock.Mock()
        # mock refund class
        Refund = mock.Mock()
        Refund.query.filter.return_value = page
        # mock debit class
        Debit = mock.Mock()
        Debit.find.return_value = debit

        processor = self.make_one(
            refund_cls=Refund,
            debit_cls=Debit,
            customer_cls=Customer,
        )
        refund_uri = processor.refund(transaction)
        self.assertEqual(refund_uri, 'MOCK_BALANCED_REFUND_URI')

        # make sure we won't duplicate refund
        self.assertFalse(debit.refund.called)
        # make sure query is made correctly
        expected_kwargs = {'meta.billy.transaction_guid': transaction.guid}
        Refund.query.filter.assert_called_once_with(**expected_kwargs)
