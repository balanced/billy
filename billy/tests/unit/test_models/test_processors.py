from __future__ import unicode_literals
import unittest
import datetime

import mock
import balanced
import transaction as db_transaction
from flexmock import flexmock
from freezegun import freeze_time

from billy.models.processors.base import PaymentProcessor
from billy.tests.unit.helper import ModelTestCase


class TestPaymentProcessorModel(unittest.TestCase):

    def test_base_processor(self):
        processor = PaymentProcessor()
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
            self.company_guid = self.company_model.create('my_secret_key')
            self.plan_guid = self.plan_model.create(
                company_guid=self.company_guid,
                plan_type=self.plan_model.TYPE_CHARGE,
                amount=10,
                frequency=self.plan_model.FREQ_MONTHLY,
            )
            self.customer_guid = self.customer_model.create(
                company_guid=self.company_guid,
                processor_uri='MOCK_BALANCED_CUSTOMER_URI',
            )
            self.subscription_guid = self.subscription_model.create(
                customer_guid=self.customer_guid,
                plan_guid=self.plan_guid,
                payment_uri='/v1/credit_card/tester',
            )
            self.invoice_guid = self.invoice_model.create(
                customer_guid=self.customer_guid,
                amount=100,
            )
        self.customer = self.customer_model.get(self.customer_guid)

    def make_one(self, *args, **kwargs):
        from billy.models.processors.balanced_payments import BalancedProcessor
        return BalancedProcessor(*args, **kwargs)

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

    def test_prepare_customer_with_none_payment_uri(self):
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

    def test_prepare_customer_with_bad_payment_uri(self):
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
        transaction_cls,
        processor_method_name, 
        api_method_name,
        extra_api_kwargs,
    ):
        tx_model = self.transaction_model
        with db_transaction.manager:
            if transaction_cls == tx_model.CLS_SUBSCRIPTION:
                guid = tx_model.create(
                    subscription_guid=self.subscription_guid,
                    transaction_cls=tx_model.CLS_SUBSCRIPTION,
                    transaction_type=tx_model.TYPE_CHARGE,
                    amount=10,
                    payment_uri='/v1/credit_card/tester',
                    appears_on_statement_as='hello baby',
                    scheduled_at=datetime.datetime.utcnow(),
                )
                transaction = tx_model.get(guid)
                description = (
                    'Generated by Billy from subscription {}, scheduled_at={}'
                    .format(
                        self.subscription_guid, 
                        transaction.scheduled_at,
                    )
                )
            elif transaction_cls == tx_model.CLS_INVOICE:
                guid = tx_model.create(
                    invoice_guid=self.invoice_guid,
                    transaction_cls=tx_model.CLS_INVOICE,
                    transaction_type=tx_model.TYPE_CHARGE,
                    amount=10,
                    payment_uri='/v1/credit_card/tester',
                    appears_on_statement_as='hello baby',
                    scheduled_at=datetime.datetime.utcnow(),
                )
                transaction = tx_model.get(guid)
                description = (
                    'Generated by Billy from invoice {}, scheduled_at={}'
                    .format(
                        self.invoice_guid, 
                        transaction.scheduled_at,
                    )
                )
            self.customer_model.update(
                guid=self.customer_guid,
                processor_uri='MOCK_BALANCED_CUSTOMER_URI',
            )
        transaction = tx_model.get(guid)

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
            description=description,
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
            guid = tx_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=tx_model.CLS_SUBSCRIPTION,
                transaction_type=tx_model.TYPE_CHARGE,
                amount=10,
                payment_uri='/v1/credit_card/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )
            transaction = tx_model.get(guid)
        transaction = tx_model.get(guid)

        # mock resource
        resource = mock.Mock(uri='MOCK_BALANCED_RESOURCE_URI')
        # mock page
        page = mock.Mock()
        page.one.return_value = resource
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
        balanced_res_uri = method(transaction)
        self.assertEqual(balanced_res_uri, 'MOCK_BALANCED_RESOURCE_URI')

        # make sure the api method is not called
        self.assertFalse(BalancedCustomer.find.called)
        self.assertFalse(api_method.called)

    def test_charge_subscription(self):
        self._test_operation(
            cls_name='debit_cls', 
            transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
            processor_method_name='charge',
            api_method_name='debit',
            extra_api_kwargs=dict(source_uri='/v1/credit_card/tester'),
        )

    def test_charge_invoice(self):
        self._test_operation(
            cls_name='debit_cls', 
            transaction_cls=self.transaction_model.CLS_INVOICE,
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

    def test_payout_subscription(self):
        self._test_operation(
            cls_name='credit_cls', 
            transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
            processor_method_name='payout',
            api_method_name='credit',
            extra_api_kwargs=dict(destination_uri='/v1/credit_card/tester'),
        )

    def test_payout_invoice(self):
        self._test_operation(
            cls_name='credit_cls', 
            transaction_cls=self.transaction_model.CLS_INVOICE,
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

    def test_refund(self):
        tx_model = self.transaction_model
        with db_transaction.manager:
            charge_guid = tx_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=tx_model.CLS_SUBSCRIPTION,
                transaction_type=tx_model.TYPE_CHARGE,
                amount=100,
                payment_uri='/v1/credit_card/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )
            charge_transaction = tx_model.get(charge_guid)
            charge_transaction.status = tx_model.STATUS_DONE
            charge_transaction.external_id = 'MOCK_BALANCED_DEBIT_URI'
            self.session.add(charge_transaction)
            self.session.flush()

            refund_guid = tx_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=tx_model.CLS_SUBSCRIPTION,
                transaction_type=tx_model.TYPE_REFUND,
                refund_to_guid=charge_guid,
                amount=56,
                scheduled_at=datetime.datetime.utcnow(),
            )

        transaction = tx_model.get(refund_guid)

        # make sure API key is set correctly
        (
            flexmock(balanced)
            .should_receive('configure')
            .with_args('my_secret_key')
            .once()
        )

        # mock result page object of balanced.Refund.query.filter(...)

        def mock_one():
            raise balanced.exc.NoResultFound

        mock_page = (
            flexmock()
            .should_receive('one')
            .replace_with(mock_one)
            .once()
            .mock()
        )

        # mock balanced.Refund.query
        mock_query = (
            flexmock()
            .should_receive('filter')
            .with_args(**{'meta.billy.transaction_guid': transaction.guid})
            .replace_with(lambda **kw: mock_page)
            .mock()
        )

        # mock balanced.Refund class
        class Refund(object): 
            pass
        Refund.query = mock_query

        # mock balanced.Refund instance
        mock_refund = flexmock(uri='MOCK_BALANCED_REFUND_URI')

        # mock balanced.Debit instance
        kwargs = dict(
            amount=transaction.amount,
            meta={'billy.transaction_guid': transaction.guid},
            description=(
                'Generated by Billy from subscription {}, scheduled_at={}'
                .format(transaction.subscription.guid, transaction.scheduled_at)
            )
        )
        mock_balanced_debit = (
            flexmock()
            .should_receive('refund')
            .with_args(**kwargs)
            .replace_with(lambda **kw: mock_refund)
            .once()
            .mock()
        )

        # mock balanced.Debit class
        class BalancedDebit(object): 
            def find(self, uri):
                pass
        (
            flexmock(BalancedDebit)
            .should_receive('find')
            .with_args('MOCK_BALANCED_DEBIT_URI')
            .replace_with(lambda _: mock_balanced_debit)
            .once()
        )

        processor = self.make_one(
            refund_cls=Refund,
            debit_cls=BalancedDebit,
        )
        refund_uri = processor.refund(transaction)
        self.assertEqual(refund_uri, 'MOCK_BALANCED_REFUND_URI')

    def test_refund_with_created_record(self):
        tx_model = self.transaction_model
        with db_transaction.manager:
            charge_guid = tx_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=tx_model.CLS_SUBSCRIPTION,
                transaction_type=tx_model.TYPE_CHARGE,
                amount=100,
                payment_uri='/v1/credit_card/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )
            charge_transaction = tx_model.get(charge_guid)
            charge_transaction.status = tx_model.STATUS_DONE
            charge_transaction.external_id = 'MOCK_BALANCED_DEBIT_URI'
            self.session.add(charge_transaction)
            self.session.flush()

            refund_guid = tx_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=tx_model.CLS_SUBSCRIPTION,
                transaction_type=tx_model.TYPE_REFUND,
                refund_to_guid=charge_guid,
                amount=56,
                scheduled_at=datetime.datetime.utcnow(),
            )

        transaction = tx_model.get(refund_guid)

        # mock balanced.Refund instance
        mock_refund = flexmock(uri='MOCK_BALANCED_REFUND_URI')

        # mock result page object of balanced.Refund.query.filter(...)

        def mock_one():
            return mock_refund

        mock_page = (
            flexmock()
            .should_receive('one')
            .replace_with(mock_one)
            .once()
            .mock()
        )

        # mock balanced.Refund.query
        mock_query = (
            flexmock()
            .should_receive('filter')
            .with_args(**{'meta.billy.transaction_guid': transaction.guid})
            .replace_with(lambda **kw: mock_page)
            .mock()
        )

        # mock balanced.Refund class
        class Refund(object): 
            pass
        Refund.query = mock_query

        processor = self.make_one(refund_cls=Refund)
        refund_uri = processor.refund(transaction)
        self.assertEqual(refund_uri, 'MOCK_BALANCED_REFUND_URI')
