from __future__ import unicode_literals
import datetime
import decimal
import contextlib

import mock
import transaction as db_transaction
from freezegun import freeze_time

from billy.models import tables
from billy.models.processors.base import PaymentProcessor
from billy.tests.unit.helper import ModelTestCase


class TestTransactionModelBase(ModelTestCase):

    def setUp(self):
        super(TestTransactionModelBase, self).setUp()
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
                funding_instrument_uri='/v1/cards/tester',
            )
            self.invoice_guid = self.invoice_model.create(
                customer_guid=self.customer_guid,
                amount=100,
            )


@freeze_time('2013-08-16')
class TestTransactionModel(TestTransactionModelBase):

    def test_get_transaction(self):
        transaction = self.transaction_model.get('TX_NON_EXIST')
        self.assertEqual(transaction, None)

        with self.assertRaises(KeyError):
            self.transaction_model.get('TX_NON_EXIST', raise_error=True)

        with db_transaction.manager:
            guid = self.transaction_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=10,
                funding_instrument_uri='/v1/cards/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )

        transaction = self.transaction_model.get(guid, raise_error=True)
        self.assertEqual(transaction.guid, guid)

    def test_list_by_company_guid(self):
        # Following code basically crerates another company with records 
        # like this:
        #
        #     + Company (other)
        #         + Customer1 (shared by two subscriptions)
        #         + Plan1
        #             + Subscription1
        #                 + Transaction1
        #         + Plan2
        #             + Subscription2
        #                 + Transaction2
        #         + Invoice1
        #             + Transaction3
        #
        with db_transaction.manager:
            other_company_guid = self.company_model.create('my_secret_key')
            other_plan_guid1 = self.plan_model.create(
                company_guid=other_company_guid,
                plan_type=self.plan_model.TYPE_CHARGE,
                amount=10,
                frequency=self.plan_model.FREQ_MONTHLY,
            )
            other_plan_guid2 = self.plan_model.create(
                company_guid=other_company_guid,
                plan_type=self.plan_model.TYPE_CHARGE,
                amount=10,
                frequency=self.plan_model.FREQ_MONTHLY,
            )
            other_customer_guid = self.customer_model.create(
                company_guid=other_company_guid,
            )
            other_subscription_guid1 = self.subscription_model.create(
                customer_guid=other_customer_guid,
                plan_guid=other_plan_guid1,
                funding_instrument_uri='/v1/cards/tester',
            )
            other_subscription_guid2 = self.subscription_model.create(
                customer_guid=other_customer_guid,
                plan_guid=other_plan_guid2,
                funding_instrument_uri='/v1/cards/tester',
            )
            other_invoice_guid = self.invoice_model.create(
                customer_guid=other_customer_guid,
                amount=100,
            )
        with db_transaction.manager:
            other_guid1 = self.transaction_model.create(
                subscription_guid=other_subscription_guid1,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=10,
                funding_instrument_uri='/v1/cards/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )
            other_guid2 = self.transaction_model.create(
                subscription_guid=other_subscription_guid2,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=10,
                funding_instrument_uri='/v1/cards/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )
            other_guid3 = self.transaction_model.create(
                invoice_guid=other_invoice_guid,
                transaction_cls=self.transaction_model.CLS_INVOICE,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=10,
                funding_instrument_uri='/v1/cards/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )
        # Following code basically crerates our records under default company
        # like this:
        #
        #     + Company (default)
        #         + Customer1
        #         + Plan1
        #             + Subscription1
        #                 + Transaction1
        #                 + Transaction2
        #                 + Transaction3
        #
        with db_transaction.manager:
            guid1 = self.transaction_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=10,
                funding_instrument_uri='/v1/cards/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )
            guid2 = self.transaction_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=10,
                funding_instrument_uri='/v1/cards/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )
            guid3 = self.transaction_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=10,
                funding_instrument_uri='/v1/cards/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )
        result_guids = [tx.guid for tx in 
                        self.transaction_model.list_by_company_guid(self.company_guid)]
        self.assertEqual(set(result_guids), set([guid1, guid2, guid3]))
        result_guids = [tx.guid for tx in 
                        self.transaction_model.list_by_company_guid(other_company_guid)]
        self.assertEqual(
            set(result_guids), 
            set([other_guid1, other_guid2, other_guid3]),
        )

    def test_list_by_subscription_guid(self):
        # Following code basically crerates records like this:
        #
        #     + Subscription1
        #         + Transaction1
        #         + Transaction2
        #         + Transaction3
        #     + Subscription2
        #         + Transaction4
        #         + Transaction5
        #
        with db_transaction.manager:
            subscription_guid1 = self.subscription_model.create(
                customer_guid=self.customer_guid,
                plan_guid=self.plan_guid,
                funding_instrument_uri='/v1/cards/tester',
            )
            # add some invoice transactions here to make sure
            # it will only return subscription transactions
            self.transaction_model.create(
                invoice_guid=self.invoice_guid,
                transaction_cls=self.transaction_model.CLS_INVOICE,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=10,
                funding_instrument_uri='/v1/cards/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )
            guid_ids1 = []
            for _ in range(3):
                guid = self.transaction_model.create(
                    subscription_guid=subscription_guid1,
                    transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                    transaction_type=self.transaction_model.TYPE_CHARGE,
                    amount=10,
                    funding_instrument_uri='/v1/cards/tester',
                    scheduled_at=datetime.datetime.utcnow(),
                )
                guid_ids1.append(guid)
            self.transaction_model.create(
                invoice_guid=self.invoice_guid,
                transaction_cls=self.transaction_model.CLS_INVOICE,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=10,
                funding_instrument_uri='/v1/cards/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )

            subscription_guid2 = self.subscription_model.create(
                customer_guid=self.customer_guid,
                plan_guid=self.plan_guid,
                funding_instrument_uri='/v1/cards/tester',
            )
            guid_ids2 = []
            for _ in range(2):
                guid = self.transaction_model.create(
                    subscription_guid=subscription_guid2,
                    transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                    transaction_type=self.transaction_model.TYPE_CHARGE,
                    amount=10,
                    funding_instrument_uri='/v1/cards/tester',
                    scheduled_at=datetime.datetime.utcnow(),
                )
                guid_ids2.append(guid)

        result_guids = [tx.guid for tx in 
                        self.transaction_model.list_by_subscription_guid(subscription_guid1)]
        self.assertEqual(set(result_guids), set(guid_ids1))

        result_guids = [tx.guid for tx in 
                        self.transaction_model.list_by_subscription_guid(subscription_guid2)]
        self.assertEqual(set(result_guids), set(guid_ids2))

    def test_list_by_company_guid_with_offset_limit(self):
        guids = []
        with db_transaction.manager:
            for i in range(10):
                with freeze_time('2013-08-16 00:00:{:02}'.format(i)):
                    guid = self.transaction_model.create(
                        subscription_guid=self.subscription_guid,
                        transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                        transaction_type=self.transaction_model.TYPE_CHARGE,
                        amount=10 * i,
                        funding_instrument_uri='/v1/cards/tester',
                        scheduled_at=datetime.datetime.utcnow(),
                    )
                    guids.append(guid)
        guids = list(reversed(guids))

        def assert_list(offset, limit, expected):
            result = self.transaction_model.list_by_company_guid(
                self.company_guid, 
                offset=offset, 
                limit=limit,
            )
            result_guids = [tx.guid for tx in result]
            self.assertEqual(set(result_guids), set(expected))
        assert_list(0, 0, [])
        assert_list(10, 10, [])
        assert_list(0, 10, guids)
        assert_list(0, 1, guids[:1])
        assert_list(1, 1, guids[1:2])
        assert_list(5, 1000, guids[5:])
        assert_list(5, 10, guids[5:])

    def test_create(self):
        subscription_guid = self.subscription_guid
        transaction_type = self.transaction_model.TYPE_CHARGE
        transaction_cls = self.transaction_model.CLS_SUBSCRIPTION
        amount = 100
        funding_instrument_uri = '/v1/cards/tester'
        appears_on_statement_as = 'hello baby'
        now = datetime.datetime.utcnow()
        scheduled_at = now + datetime.timedelta(days=1)

        with db_transaction.manager:
            guid = self.transaction_model.create(
                subscription_guid=subscription_guid,
                transaction_cls=transaction_cls,
                transaction_type=transaction_type,
                amount=amount,
                funding_instrument_uri=funding_instrument_uri,
                appears_on_statement_as=appears_on_statement_as,
                scheduled_at=scheduled_at,
            )

        transaction = self.transaction_model.get(guid)
        self.assertEqual(transaction.guid, guid)
        self.assert_(transaction.guid.startswith('TX'))
        self.assertEqual(transaction.subscription_guid, subscription_guid)
        self.assertEqual(transaction.transaction_type, transaction_type)
        self.assertEqual(transaction.transaction_cls, transaction_cls)
        self.assertEqual(transaction.amount, amount)
        self.assertEqual(transaction.funding_instrument_uri, funding_instrument_uri)
        self.assertEqual(transaction.appears_on_statement_as, 
                         appears_on_statement_as)
        self.assertEqual(transaction.status, self.transaction_model.STATUS_INIT)
        self.assertEqual(transaction.failure_count, 0)
        self.assertEqual(transaction.error_message, None)
        self.assertEqual(transaction.scheduled_at, scheduled_at)
        self.assertEqual(transaction.created_at, now)
        self.assertEqual(transaction.updated_at, now)

    def test_create_different_created_updated_time(self):
        results = [
            datetime.datetime(2013, 8, 16, 1),
            datetime.datetime(2013, 8, 16, 2),
        ]

        def mock_utcnow():
            return results.pop(0)

        tables.set_now_func(mock_utcnow)

        with db_transaction.manager:
            guid = self.transaction_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=100,
                funding_instrument_uri='/v1/cards/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )

        transaction = self.transaction_model.get(guid)
        self.assertEqual(transaction.created_at, transaction.updated_at)

    def test_create_refund(self):
        now = datetime.datetime.utcnow()

        with db_transaction.manager:
            tx_guid = self.transaction_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=100,
                funding_instrument_uri='/v1/cards/tester',
                scheduled_at=now,
            )

        with db_transaction.manager:
            refund_guid = self.transaction_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_REFUND,
                refund_to_guid=tx_guid, 
                amount=50,
                scheduled_at=now,
            )

        refund_transaction = self.transaction_model.get(refund_guid)
        self.assertEqual(refund_transaction.refund_to_guid, tx_guid)
        self.assertEqual(refund_transaction.refund_to.guid, tx_guid)
        self.assertEqual(refund_transaction.refund_to.refund_from.guid, 
                         refund_guid)
        self.assertEqual(refund_transaction.transaction_type, self.transaction_model.TYPE_REFUND)
        self.assertEqual(refund_transaction.amount, decimal.Decimal(50))

    def test_create_refund_with_non_exist_target(self):
        now = datetime.datetime.utcnow()

        with self.assertRaises(KeyError):
            self.transaction_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_REFUND,
                refund_to_guid='TX_NON_EXIST', 
                amount=50,
                scheduled_at=now,
            )

    def test_create_refund_with_wrong_transaction_type(self):
        now = datetime.datetime.utcnow()

        with self.assertRaises(ValueError):
            tx_guid = self.transaction_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=100,
                funding_instrument_uri='/v1/cards/tester',
                scheduled_at=now,
            )
            self.transaction_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_PAYOUT,
                refund_to_guid=tx_guid, 
                amount=50,
                scheduled_at=now,
            )

    def test_create_refund_with_funding_instrument_uri(self):
        now = datetime.datetime.utcnow()

        with self.assertRaises(ValueError):
            tx_guid = self.transaction_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=100,
                funding_instrument_uri='/v1/cards/tester',
                scheduled_at=now,
            )
            self.transaction_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_REFUND,
                refund_to_guid=tx_guid, 
                amount=50,
                scheduled_at=now,
                funding_instrument_uri='/v1/cards/tester',
            )

    def test_create_refund_with_wrong_target(self):
        now = datetime.datetime.utcnow()

        with db_transaction.manager:
            tx_guid = self.transaction_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=100,
                funding_instrument_uri='/v1/cards/tester',
                scheduled_at=now,
            )
            refund_guid = self.transaction_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_REFUND,
                refund_to_guid=tx_guid, 
                amount=50,
                scheduled_at=now,
            )

        with self.assertRaises(ValueError):
            self.transaction_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_REFUND,
                refund_to_guid=refund_guid, 
                amount=50,
                scheduled_at=now,
            )

        with db_transaction.manager:
            tx_guid = self.transaction_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_PAYOUT,
                amount=100,
                funding_instrument_uri='/v1/cards/tester',
                scheduled_at=now,
            )

        with self.assertRaises(ValueError):
            self.transaction_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_REFUND,
                refund_to_guid=refund_guid, 
                amount=50,
                scheduled_at=now,
            )

    def test_create_with_wrong_type(self):
        with self.assertRaises(ValueError):
            self.transaction_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=999,
                amount=123,
                funding_instrument_uri='/v1/cards/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )

    def test_create_with_wrong_cls(self):
        with self.assertRaises(ValueError):
            self.transaction_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=999,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=123,
                funding_instrument_uri='/v1/cards/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )

    def test_create_with_none_guid(self):
        with self.assertRaises(ValueError):
            self.transaction_model.create(
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=123,
                funding_instrument_uri='/v1/cards/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )
        with self.assertRaises(ValueError):
            self.transaction_model.create(
                transaction_cls=self.transaction_model.CLS_INVOICE,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=123,
                funding_instrument_uri='/v1/cards/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )

    def test_update(self):
        with db_transaction.manager:
            guid = self.transaction_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=10,
                funding_instrument_uri='/v1/cards/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )

        transaction = self.transaction_model.get(guid)
        status = self.transaction_model.STATUS_DONE

        with db_transaction.manager:
            self.transaction_model.update(
                guid=guid,
                status=status,
            )

        transaction = self.transaction_model.get(guid)
        self.assertEqual(transaction.status, status)

    def test_update_updated_at(self):
        with db_transaction.manager:
            guid = self.transaction_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=10,
                funding_instrument_uri='/v1/cards/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )

        transaction = self.transaction_model.get(guid)
        created_at = transaction.created_at

        # advanced the current date time
        with contextlib.nested(
            freeze_time('2013-08-16 07:00:01'),
            db_transaction.manager,
        ):
            self.transaction_model.update(guid=guid)
            updated_at = datetime.datetime.utcnow()

        transaction = self.transaction_model.get(guid)
        self.assertEqual(transaction.updated_at, updated_at)
        self.assertEqual(transaction.created_at, created_at)

        # advanced the current date time even more
        with contextlib.nested(
            freeze_time('2013-08-16 08:35:40'),
            db_transaction.manager,
        ):
            # this should update the updated_at field only
            self.transaction_model.update(guid)
            updated_at = datetime.datetime.utcnow()

        transaction = self.transaction_model.get(guid)
        self.assertEqual(transaction.updated_at, updated_at)
        self.assertEqual(transaction.created_at, created_at)

    def test_update_with_wrong_args(self):
        with db_transaction.manager:
            guid = self.transaction_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=10,
                funding_instrument_uri='/v1/cards/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )

        # make sure passing wrong argument will raise error
        with self.assertRaises(TypeError):
            self.transaction_model.update(
                guid=guid, 
                wrong_arg=True, 
                status=self.transaction_model.STATUS_INIT
            )

    def test_update_with_wrong_status(self):
        with db_transaction.manager:
            guid = self.transaction_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=10,
                funding_instrument_uri='/v1/cards/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )

        with self.assertRaises(ValueError):
            self.transaction_model.update(
                guid=guid,
                status=999,
            )

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

    def test_get_last_transaction(self):
        guids = []
        for dt in ['2013-08-17', '2013-08-15', '2013-08-15']:
            with contextlib.nested(
                freeze_time(dt),
                db_transaction.manager,
            ):
                guid = self.transaction_model.create(
                    subscription_guid=self.subscription_guid,
                    transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                    transaction_type=self.transaction_model.TYPE_CHARGE,
                    amount=10,
                    funding_instrument_uri='/v1/cards/tester',
                    scheduled_at=datetime.datetime.utcnow(),
                )
                guids.append(guid)
        self.assertEqual(self.transaction_model.get_last_transaction().guid, 
                         guids[0])


@freeze_time('2013-08-16')
class TestProcessSubscriptionTransaction(TestTransactionModelBase):

    def setUp(self):
        super(TestProcessSubscriptionTransaction, self).setUp()

    def _create_transaction(self, tx_type):
        with db_transaction.manager:
            transaction_guid = self.transaction_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=tx_type,
                amount=100,
                funding_instrument_uri='/v1/cards/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )
        transaction = self.transaction_model.get(transaction_guid)
        return transaction

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.charge')
    def test_process_one_charge(self, charge_method):
        now = datetime.datetime.utcnow()
        transaction = self._create_transaction(
            self.transaction_model.TYPE_CHARGE,
        )
        charge_method.return_value = 'MOCK_DEBIT_URI'

        with contextlib.nested(
            freeze_time('2013-08-20'),
            db_transaction.manager,
        ):
            self.transaction_model.process_one(transaction)
            updated_at = datetime.datetime.utcnow()

        charge_method.assert_called_once_with(transaction)
        self.assertEqual(transaction.transaction_type, 
                         self.transaction_model.TYPE_CHARGE)
        self.assertEqual(transaction.status, self.transaction_model.STATUS_DONE)
        self.assertEqual(transaction.processor_uri, 'MOCK_DEBIT_URI')
        self.assertEqual(transaction.updated_at, updated_at)
        self.assertEqual(transaction.scheduled_at, now)
        self.assertEqual(transaction.created_at, now)
        self.assertEqual(transaction.subscription.customer.processor_uri, 
                         'MOCK_CUSTOMER_URI')

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.payout')
    def test_process_one_payout(self, payout_method):
        transaction = self._create_transaction(
            self.transaction_model.TYPE_PAYOUT,
        )
        payout_method.return_value = 'MOCK_CREDIT_URI'

        with contextlib.nested(
            freeze_time('2013-08-20'),
            db_transaction.manager,
        ):
            self.transaction_model.process_one(transaction)

        payout_method.assert_called_once_with(transaction)
        self.assertEqual(transaction.transaction_type, 
                         self.transaction_model.TYPE_PAYOUT)

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.charge')
    def test_process_one_with_failure(self, charge_method):
        transaction = self._create_transaction(
            self.transaction_model.TYPE_CHARGE,
        )
        charge_method.side_effect = RuntimeError('Failed to charge')

        with db_transaction.manager:
            self.transaction_model.process_one(transaction)
            updated_at = datetime.datetime.utcnow()

        self.assertEqual(transaction.status, self.transaction_model.STATUS_RETRYING)
        self.assertEqual(transaction.updated_at, updated_at)
        self.assertEqual(transaction.failure_count, 1)
        self.assertEqual(transaction.error_message, 'Failed to charge')
        self.assertEqual(transaction.subscription.customer.processor_uri, 
                         'MOCK_CUSTOMER_URI')

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.charge')
    def test_process_one_with_failure_exceed_limitation(self, charge_method):
        self.model_factory.settings['billy.transaction.maximum_retry'] = 3
        transaction = self._create_transaction(
            self.transaction_model.TYPE_CHARGE,
        )

        charge_method.side_effect = RuntimeError('Failed to charge')

        for _ in range(3):
            with db_transaction.manager:
                self.transaction_model.process_one(transaction)
            self.assertEqual(transaction.status, self.transaction_model.STATUS_RETRYING)
        with db_transaction.manager:
            self.transaction_model.process_one(transaction)
        self.assertEqual(transaction.status, self.transaction_model.STATUS_FAILED)

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.prepare_customer')
    def test_process_one_with_system_exit_and_keyboard_interrupt(
        self, 
        prepare_customer_method
    ):
        transaction = self._create_transaction(
            self.transaction_model.TYPE_CHARGE,
        )

        prepare_customer_method.side_effect = SystemExit
        with self.assertRaises(SystemExit):
            self.transaction_model.process_one(transaction)

        prepare_customer_method.side_effect = KeyboardInterrupt
        with self.assertRaises(KeyboardInterrupt):
            self.transaction_model.process_one(transaction)

    def test_process_one_with_already_done(self):
        transaction = self._create_transaction(
            self.transaction_model.TYPE_CHARGE,
        )
        with db_transaction.manager:
            transaction.status = self.transaction_model.STATUS_DONE
        with self.assertRaises(ValueError):
            self.transaction_model.process_one(transaction)

    def test_process_transactions(self):
        now = datetime.datetime.utcnow()
        funding_instrument_uri = '/v1/cards/tester'

        with db_transaction.manager:
            guid1 = self.transaction_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=100,
                funding_instrument_uri=funding_instrument_uri,
                scheduled_at=now,
            )

            guid2 = self.transaction_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=100,
                funding_instrument_uri=funding_instrument_uri,
                scheduled_at=now,
            )
            self.transaction_model.update(guid2, status=self.transaction_model.STATUS_RETRYING)

            guid3 = self.transaction_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=100,
                funding_instrument_uri=funding_instrument_uri,
                scheduled_at=now,
            )
            
            guid4 = self.transaction_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=100,
                funding_instrument_uri=funding_instrument_uri,
                scheduled_at=now,
            )
            self.transaction_model.update(guid4, status=self.transaction_model.STATUS_DONE)

        with db_transaction.manager:
            tx_guids = self.transaction_model.process_transactions()
        self.assertEqual(set(tx_guids), set([guid1, guid2, guid3]))


@freeze_time('2013-08-16')
class TestProcessInvoiceTransaction(TestTransactionModelBase):

    def setUp(self):
        super(TestProcessInvoiceTransaction, self).setUp()
        self.funding_instrument_uri = '/v1/cards/tester'
        with db_transaction.manager:
            self.invoice_model.update_funding_instrument_uri(
                self.invoice_guid, 
                self.funding_instrument_uri,
            )

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.charge')
    def test_process_one_charge(self, charge_method):
        now = datetime.datetime.utcnow()
        invoice = self.invoice_model.get(self.invoice_guid)
        transaction = invoice.transactions[0]
        charge_method.return_value = 'MOCK_DEBIT_URI'
        
        with contextlib.nested(
            freeze_time('2013-08-20'),
            db_transaction.manager,
        ):
            self.transaction_model.process_one(transaction)
            updated_at = datetime.datetime.utcnow()

        charge_method.assert_called_once_with(transaction)
        self.assertEqual(transaction.status, self.transaction_model.STATUS_DONE)
        self.assertEqual(transaction.processor_uri, 'MOCK_DEBIT_URI')
        self.assertEqual(transaction.updated_at, updated_at)
        self.assertEqual(transaction.scheduled_at, now)
        self.assertEqual(transaction.created_at, now)
        self.assertEqual(transaction.invoice.customer.processor_uri, 
                         'MOCK_CUSTOMER_URI')
        self.assertEqual(invoice.status, self.invoice_model.STATUS_SETTLED)

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.refund')
    def test_process_one_refund(self, refund_method):
        self.test_process_one_charge()

        with db_transaction.manager:
            invoice = self.invoice_model.get(self.invoice_guid)
            invoice.status = self.invoice_model.STATUS_REFUNDING
            guid = self.transaction_model.create(
                invoice_guid=self.invoice_guid,
                transaction_cls=self.transaction_model.CLS_INVOICE,
                transaction_type=self.transaction_model.TYPE_REFUND,
                amount=invoice.amount,
                scheduled_at=datetime.datetime.utcnow(),
            )

        invoice = self.invoice_model.get(self.invoice_guid)
        transaction = self.transaction_model.get(guid)

        refund_method.return_value = 'MOCK_REFUND_URI'

        with contextlib.nested(
            freeze_time('2013-08-20'),
            db_transaction.manager,
        ):
            self.session.add(transaction)
            self.transaction_model.process_one(transaction)

        refund_method.assert_called_once_with(transaction)
        self.assertEqual(transaction.status, self.transaction_model.STATUS_DONE)
        self.assertEqual(transaction.processor_uri, 'MOCK_REFUND_URI')
        self.assertEqual(transaction.invoice.customer.processor_uri, 
                         'MOCK_CUSTOMER_URI')
        self.assertEqual(invoice.status, self.invoice_model.STATUS_REFUNDED)

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.prepare_customer')
    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.charge')
    def test_process_one_with_failure_exceed_limitation(
        self, 
        charge, 
        prepare_customer,
    ):
        self.model_factory.settings['billy.transaction.maximum_retry'] = 3

        invoice = self.invoice_model.get(self.invoice_guid)
        transaction = invoice.transactions[0]

        charge.side_effect = RuntimeError('Failed to charge')
        # 3 retrying ...
        for _ in range(3):
            with db_transaction.manager:
                self.session.add(transaction)
                self.transaction_model.process_one(transaction)
            self.session.add(transaction)
            self.assertEqual(transaction.status, 
                             self.transaction_model.STATUS_RETRYING)
            invoice = self.invoice_model.get(self.invoice_guid)
            self.assertEqual(invoice.status, 
                             self.invoice_model.STATUS_PROCESSING)
        # eventually failed
        with db_transaction.manager:
            self.session.add(transaction)
            self.transaction_model.process_one(transaction)

        self.assertEqual(transaction.status, 
                         self.transaction_model.STATUS_FAILED)
        self.assertEqual(invoice.status, 
                         self.invoice_model.STATUS_PROCESS_FAILED)
        self.assertEqual(prepare_customer.call_count, 4)
        self.assertEqual(charge.call_count, 4)
