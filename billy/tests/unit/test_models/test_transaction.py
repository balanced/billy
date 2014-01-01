from __future__ import unicode_literals
import datetime
import decimal

import transaction as db_transaction
from flexmock import flexmock
from freezegun import freeze_time

from billy.models import tables
from billy.models.processors.base import PaymentProcessor
from billy.tests.unit.helper import ModelTestCase


class TestTransactionModelBase(ModelTestCase):

    def setUp(self):
        super(TestTransactionModelBase, self).setUp()

    def _create_records(self, processor_uri=None):
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
                processor_uri=processor_uri,
            )
            self.subscription_guid = self.subscription_model.create(
                customer_guid=self.customer_guid,
                plan_guid=self.plan_guid,
                payment_uri='/v1/cards/tester',
            )
            self.invoice_guid = self.invoice_model.create(
                customer_guid=self.customer_guid,
                amount=100,
            )


@freeze_time('2013-08-16')
class TestTransactionModel(TestTransactionModelBase):

    def test_get_transaction(self):
        self._create_records()
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
                payment_uri='/v1/cards/tester',
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
        self._create_records()
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
                payment_uri='/v1/cards/tester',
            )
            other_subscription_guid2 = self.subscription_model.create(
                customer_guid=other_customer_guid,
                plan_guid=other_plan_guid2,
                payment_uri='/v1/cards/tester',
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
                payment_uri='/v1/cards/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )
            other_guid2 = self.transaction_model.create(
                subscription_guid=other_subscription_guid2,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=10,
                payment_uri='/v1/cards/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )
            other_guid3 = self.transaction_model.create(
                invoice_guid=other_invoice_guid,
                transaction_cls=self.transaction_model.CLS_INVOICE,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=10,
                payment_uri='/v1/cards/tester',
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
                payment_uri='/v1/cards/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )
            guid2 = self.transaction_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=10,
                payment_uri='/v1/cards/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )
            guid3 = self.transaction_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=10,
                payment_uri='/v1/cards/tester',
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
        self._create_records()
        with db_transaction.manager:
            subscription_guid1 = self.subscription_model.create(
                customer_guid=self.customer_guid,
                plan_guid=self.plan_guid,
                payment_uri='/v1/cards/tester',
            )
            # add some invoice transactions here to make sure
            # it will only return subscription transactions
            self.transaction_model.create(
                invoice_guid=self.invoice_guid,
                transaction_cls=self.transaction_model.CLS_INVOICE,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=10,
                payment_uri='/v1/cards/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )
            guid_ids1 = []
            for _ in range(3):
                guid = self.transaction_model.create(
                    subscription_guid=subscription_guid1,
                    transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                    transaction_type=self.transaction_model.TYPE_CHARGE,
                    amount=10,
                    payment_uri='/v1/cards/tester',
                    scheduled_at=datetime.datetime.utcnow(),
                )
                guid_ids1.append(guid)
            self.transaction_model.create(
                invoice_guid=self.invoice_guid,
                transaction_cls=self.transaction_model.CLS_INVOICE,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=10,
                payment_uri='/v1/cards/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )

            subscription_guid2 = self.subscription_model.create(
                customer_guid=self.customer_guid,
                plan_guid=self.plan_guid,
                payment_uri='/v1/cards/tester',
            )
            guid_ids2 = []
            for _ in range(2):
                guid = self.transaction_model.create(
                    subscription_guid=subscription_guid2,
                    transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                    transaction_type=self.transaction_model.TYPE_CHARGE,
                    amount=10,
                    payment_uri='/v1/cards/tester',
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
        self._create_records()
        guids = []
        with db_transaction.manager:
            for i in range(10):
                with freeze_time('2013-08-16 00:00:{:02}'.format(i)):
                    guid = self.transaction_model.create(
                        subscription_guid=self.subscription_guid,
                        transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                        transaction_type=self.transaction_model.TYPE_CHARGE,
                        amount=10 * i,
                        payment_uri='/v1/cards/tester',
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
        self._create_records()
        subscription_guid = self.subscription_guid
        transaction_type = self.transaction_model.TYPE_CHARGE
        transaction_cls = self.transaction_model.CLS_SUBSCRIPTION
        amount = 100
        payment_uri = '/v1/cards/tester'
        appears_on_statement_as = 'hello baby'
        now = datetime.datetime.utcnow()
        scheduled_at = now + datetime.timedelta(days=1)

        with db_transaction.manager:
            guid = self.transaction_model.create(
                subscription_guid=subscription_guid,
                transaction_cls=transaction_cls,
                transaction_type=transaction_type,
                amount=amount,
                payment_uri=payment_uri,
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
        self.assertEqual(transaction.payment_uri, payment_uri)
        self.assertEqual(transaction.appears_on_statement_as, 
                         appears_on_statement_as)
        self.assertEqual(transaction.status, self.transaction_model.STATUS_INIT)
        self.assertEqual(transaction.failure_count, 0)
        self.assertEqual(transaction.error_message, None)
        self.assertEqual(transaction.scheduled_at, scheduled_at)
        self.assertEqual(transaction.created_at, now)
        self.assertEqual(transaction.updated_at, now)

    def test_create_different_created_updated_time(self):
        self._create_records()
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
                payment_uri='/v1/cards/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )

        transaction = self.transaction_model.get(guid)
        self.assertEqual(transaction.created_at, transaction.updated_at)

    def test_create_refund(self):
        self._create_records()
        now = datetime.datetime.utcnow()

        with db_transaction.manager:
            tx_guid = self.transaction_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=100,
                payment_uri='/v1/cards/tester',
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
        self._create_records()
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
        self._create_records()
        now = datetime.datetime.utcnow()

        with self.assertRaises(ValueError):
            tx_guid = self.transaction_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=100,
                payment_uri='/v1/cards/tester',
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

    def test_create_refund_with_payment_uri(self):
        self._create_records()
        now = datetime.datetime.utcnow()

        with self.assertRaises(ValueError):
            tx_guid = self.transaction_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=100,
                payment_uri='/v1/cards/tester',
                scheduled_at=now,
            )
            self.transaction_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_REFUND,
                refund_to_guid=tx_guid, 
                amount=50,
                scheduled_at=now,
                payment_uri='/v1/cards/tester',
            )

    def test_create_refund_with_wrong_target(self):
        self._create_records()
        now = datetime.datetime.utcnow()

        with db_transaction.manager:
            tx_guid = self.transaction_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=100,
                payment_uri='/v1/cards/tester',
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
                payment_uri='/v1/cards/tester',
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
        self._create_records()
        with self.assertRaises(ValueError):
            self.transaction_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=999,
                amount=123,
                payment_uri='/v1/cards/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )

    def test_create_with_wrong_cls(self):
        self._create_records()
        with self.assertRaises(ValueError):
            self.transaction_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=999,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=123,
                payment_uri='/v1/cards/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )

    def test_create_with_none_guid(self):
        self._create_records()
        with self.assertRaises(ValueError):
            self.transaction_model.create(
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=123,
                payment_uri='/v1/cards/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )
        with self.assertRaises(ValueError):
            self.transaction_model.create(
                transaction_cls=self.transaction_model.CLS_INVOICE,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=123,
                payment_uri='/v1/cards/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )

    def test_update(self):
        self._create_records()
        with db_transaction.manager:
            guid = self.transaction_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=10,
                payment_uri='/v1/cards/tester',
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
        self._create_records()
        with db_transaction.manager:
            guid = self.transaction_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=10,
                payment_uri='/v1/cards/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )

        transaction = self.transaction_model.get(guid)
        created_at = transaction.created_at

        # advanced the current date time
        with freeze_time('2013-08-16 07:00:01'):
            with db_transaction.manager:
                self.transaction_model.update(guid=guid)
            updated_at = datetime.datetime.utcnow()

        transaction = self.transaction_model.get(guid)
        self.assertEqual(transaction.updated_at, updated_at)
        self.assertEqual(transaction.created_at, created_at)

        # advanced the current date time even more
        with freeze_time('2013-08-16 08:35:40'):
            # this should update the updated_at field only
            with db_transaction.manager:
                self.transaction_model.update(guid)
            updated_at = datetime.datetime.utcnow()

        transaction = self.transaction_model.get(guid)
        self.assertEqual(transaction.updated_at, updated_at)
        self.assertEqual(transaction.created_at, created_at)

    def test_update_with_wrong_args(self):
        self._create_records()
        with db_transaction.manager:
            guid = self.transaction_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=10,
                payment_uri='/v1/cards/tester',
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
        self._create_records()
        with db_transaction.manager:
            guid = self.transaction_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=10,
                payment_uri='/v1/cards/tester',
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

    def test_process_one_charge(self):
        self._create_records()
        now = datetime.datetime.utcnow()
        payment_uri = '/v1/cards/tester'

        with db_transaction.manager:
            guid = self.transaction_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=100,
                payment_uri=payment_uri,
                scheduled_at=now,
            )

        transaction = self.transaction_model.get(guid)
        customer = transaction.subscription.customer

        mock_processor = flexmock(
            payout=None,
            refund=None,
        )
        (
            mock_processor 
            .should_receive('create_customer')
            .with_args(customer)
            .replace_with(lambda c: 'AC_MOCK')
            .once()
        )
        (
            mock_processor 
            .should_receive('prepare_customer')
            .with_args(customer, payment_uri)
            .replace_with(lambda c, payment_uri: None)
            .once()
        )
        (
            mock_processor 
            .should_receive('charge')
            .with_args(transaction)
            .replace_with(lambda t: 'TX_MOCK')
            .once()
        )

        with freeze_time('2013-08-20'):
            with db_transaction.manager:
                self.transaction_model.process_one(mock_processor, transaction)
                updated_at = datetime.datetime.utcnow()

        transaction = self.transaction_model.get(guid)
        self.assertEqual(transaction.status, self.transaction_model.STATUS_DONE)
        self.assertEqual(transaction.external_id, 'TX_MOCK')
        self.assertEqual(transaction.updated_at, updated_at)
        self.assertEqual(transaction.scheduled_at, now)
        self.assertEqual(transaction.created_at, now)
        self.assertEqual(transaction.subscription.customer.processor_uri, 
                         'AC_MOCK')

    def test_process_one_payout(self):
        self._create_records()
        now = datetime.datetime.utcnow()
        payment_uri = '/v1/cards/tester'

        with db_transaction.manager:
            guid = self.transaction_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_PAYOUT,
                amount=100,
                payment_uri=payment_uri,
                scheduled_at=now,
            )

        transaction = self.transaction_model.get(guid)
        customer = transaction.subscription.customer

        mock_processor = flexmock(
            charge=None,
            refund=None,
        )
        (
            mock_processor 
            .should_receive('create_customer')
            .with_args(customer)
            .replace_with(lambda c: 'AC_MOCK')
            .once()
        )
        (
            mock_processor 
            .should_receive('prepare_customer')
            .with_args(customer, payment_uri)
            .replace_with(lambda c, payment_uri: None)
            .once()
        )
        (
            mock_processor 
            .should_receive('payout')
            .with_args(transaction)
            .replace_with(lambda t: 'TX_MOCK')
            .once()
        )

        with freeze_time('2013-08-20'):
            with db_transaction.manager:
                self.transaction_model.process_one(mock_processor, transaction)
                updated_at = datetime.datetime.utcnow()

        transaction = self.transaction_model.get(guid)
        self.assertEqual(transaction.status, self.transaction_model.STATUS_DONE)
        self.assertEqual(transaction.external_id, 'TX_MOCK')
        self.assertEqual(transaction.updated_at, updated_at)
        self.assertEqual(transaction.scheduled_at, now)
        self.assertEqual(transaction.created_at, now)
        self.assertEqual(transaction.subscription.customer.processor_uri, 
                         'AC_MOCK')

    def test_process_one_with_failure(self):
        self._create_records()
        now = datetime.datetime.utcnow()
        payment_uri = '/v1/cards/tester'

        with db_transaction.manager:
            guid = self.transaction_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=100,
                payment_uri=payment_uri,
                scheduled_at=now,
            )

        transaction = self.transaction_model.get(guid)
        customer = transaction.subscription.customer

        def mock_charge(transaction):
            raise RuntimeError('Failed to charge')

        mock_processor = flexmock(
            payout=None,
            refund=None,
        )
        (
            mock_processor 
            .should_receive('create_customer')
            .with_args(customer)
            .replace_with(lambda c: 'AC_MOCK')
            .once()
        )
        (
            mock_processor 
            .should_receive('prepare_customer')
            .with_args(customer, payment_uri)
            .replace_with(lambda c, payment_uri: None)
            .once()
        )
        (
            mock_processor 
            .should_receive('charge')
            .with_args(transaction)
            .replace_with(mock_charge)
            .once()
        )

        with db_transaction.manager:
            self.transaction_model.process_one(mock_processor, transaction)
            updated_at = datetime.datetime.utcnow()

        transaction = self.transaction_model.get(guid)
        self.assertEqual(transaction.status, self.transaction_model.STATUS_RETRYING)
        self.assertEqual(transaction.updated_at, updated_at)
        self.assertEqual(transaction.failure_count, 1)
        self.assertEqual(transaction.error_message, 'Failed to charge')
        self.assertEqual(transaction.subscription.customer.processor_uri, 
                         'AC_MOCK')

    def test_process_one_with_failure_exceed_limitation(self):
        self._create_records('AC_MOCK')
        payment_uri = '/v1/cards/tester'
        self.transaction_model.maximum_retry = 3
        now = datetime.datetime.utcnow()

        with db_transaction.manager:
            guid = self.transaction_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=100,
                payment_uri=payment_uri,
                scheduled_at=now,
            )

        transaction = self.transaction_model.get(guid)

        def mock_charge(transaction):
            raise RuntimeError('Failed to charge')

        mock_processor = flexmock(
            payout=None,
            refund=None,
        )
        (
            mock_processor 
            .should_receive('prepare_customer')
            .replace_with(lambda c, payment_uri: None)
            .times(4)
        )
        (
            mock_processor 
            .should_receive('charge')
            .replace_with(mock_charge)
            .times(4)
        )

        for _ in range(3):
            with db_transaction.manager:
                transaction = self.transaction_model.get(guid)
                self.transaction_model.process_one(
                    processor=mock_processor, 
                    transaction=transaction, 
                )
            transaction = self.transaction_model.get(guid)
            self.assertEqual(transaction.status, self.transaction_model.STATUS_RETRYING)
        with db_transaction.manager:
            transaction = self.transaction_model.get(guid)
            self.transaction_model.process_one(
                processor=mock_processor, 
                transaction=transaction, 
            )
        transaction = self.transaction_model.get(guid)
        self.assertEqual(transaction.status, self.transaction_model.STATUS_FAILED)

    def test_process_one_with_system_exit_and_keyboard_interrupt(self):
        self._create_records()
        now = datetime.datetime.utcnow()
        payment_uri = '/v1/cards/tester'

        with db_transaction.manager:
            guid = self.transaction_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=100,
                payment_uri=payment_uri,
                scheduled_at=now,
            )

        transaction = self.transaction_model.get(guid)

        def mock_create_customer_system_exit(transaction):
            raise SystemExit

        mock_processor = flexmock(
            charge=None,
            payout=None,
            refund=None,
        )
        (
            mock_processor 
            .should_receive('create_customer')
            .replace_with(mock_create_customer_system_exit)
        )

        with self.assertRaises(SystemExit):
            self.transaction_model.process_one(mock_processor, transaction)

        def mock_create_customer_keyboard_interrupt(transaction):
            raise KeyboardInterrupt

        mock_processor = flexmock(
            charge=None,
            payout=None,
            refund=None,
        )
        (
            mock_processor 
            .should_receive('create_customer')
            .replace_with(mock_create_customer_keyboard_interrupt)
        )

        with self.assertRaises(KeyboardInterrupt):
            self.transaction_model.process_one(mock_processor, transaction)

    def test_process_one_with_already_done(self):
        self._create_records('AC_MOCK')
        now = datetime.datetime.utcnow()
        payment_uri = '/v1/cards/tester'

        with db_transaction.manager:
            guid = self.transaction_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=100,
                payment_uri=payment_uri,
                scheduled_at=now,
            )
            transaction = self.transaction_model.get(guid)
            transaction.status = self.transaction_model.STATUS_DONE
            self.session.add(transaction)

        processor = flexmock()
        transaction = self.transaction_model.get(guid)
        with self.assertRaises(ValueError):
            self.transaction_model.process_one(processor, transaction)

    def test_process_transactions(self):
        self._create_records()
        now = datetime.datetime.utcnow()
        payment_uri = '/v1/cards/tester'

        with db_transaction.manager:
            guid1 = self.transaction_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=100,
                payment_uri=payment_uri,
                scheduled_at=now,
            )

            guid2 = self.transaction_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=100,
                payment_uri=payment_uri,
                scheduled_at=now,
            )
            self.transaction_model.update(guid2, status=self.transaction_model.STATUS_RETRYING)

            guid3 = self.transaction_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=100,
                payment_uri=payment_uri,
                scheduled_at=now,
            )
            
            guid4 = self.transaction_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=100,
                payment_uri=payment_uri,
                scheduled_at=now,
            )
            self.transaction_model.update(guid4, status=self.transaction_model.STATUS_DONE)

        processor = flexmock(
            charge=None,
            payout=None,
            refund=None,
        )
        with db_transaction.manager:
            tx_guids = self.transaction_model.process_transactions(processor)

        self.assertEqual(set(tx_guids), set([guid1, guid2, guid3]))

    def test_get_last_transaction(self):
        self._create_records()
        guids = []
        for dt in ['2013-08-17', '2013-08-15', '2013-08-15']:
            with freeze_time(dt):
                with db_transaction.manager:
                    guid = self.transaction_model.create(
                        subscription_guid=self.subscription_guid,
                        transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                        transaction_type=self.transaction_model.TYPE_CHARGE,
                        amount=10,
                        payment_uri='/v1/cards/tester',
                        scheduled_at=datetime.datetime.utcnow(),
                    )
                    guids.append(guid)
        self.assertEqual(self.transaction_model.get_last_transaction().guid, 
                         guids[0])


@freeze_time('2013-08-16')
class TestInvoiceTransactionModel(TestTransactionModelBase):

    def test_process_one_charge(self):
        self._create_records()
        now = datetime.datetime.utcnow()
        payment_uri = '/v1/cards/tester'

        with db_transaction.manager:
            self.invoice_model.update_payment_uri(self.invoice_guid, payment_uri)

        invoice = self.invoice_model.get(self.invoice_guid)
        transaction = invoice.transactions[0]
        customer = transaction.invoice.customer
        guid = transaction.guid

        mock_processor = flexmock(
            payout=None,
            refund=None,
        )
        (
            mock_processor 
            .should_receive('create_customer')
            .with_args(customer)
            .replace_with(lambda c: 'AC_MOCK')
            .once()
        )
        (
            mock_processor 
            .should_receive('prepare_customer')
            .with_args(customer, payment_uri)
            .replace_with(lambda c, payment_uri: None)
            .once()
        )
        (
            mock_processor 
            .should_receive('charge')
            .with_args(transaction)
            .replace_with(lambda t: 'TX_MOCK')
            .once()
        )

        with freeze_time('2013-08-20'):
            with db_transaction.manager:
                self.transaction_model.process_one(mock_processor, transaction)
                updated_at = datetime.datetime.utcnow()

        transaction = self.transaction_model.get(guid)
        self.assertEqual(transaction.status, self.transaction_model.STATUS_DONE)
        self.assertEqual(transaction.external_id, 'TX_MOCK')
        self.assertEqual(transaction.updated_at, updated_at)
        self.assertEqual(transaction.scheduled_at, now)
        self.assertEqual(transaction.created_at, now)
        self.assertEqual(transaction.invoice.customer.processor_uri, 'AC_MOCK')

        invoice = self.invoice_model.get(self.invoice_guid)
        self.assertEqual(invoice.status, self.invoice_model.STATUS_SETTLED)

    def test_process_one_refund(self):
        self._create_records()
        now = datetime.datetime.utcnow()

        payment_uri = '/v1/cards/tester'

        with db_transaction.manager:
            self.invoice_model.update_payment_uri(self.invoice_guid, payment_uri)
            invoice = self.invoice_model.get(self.invoice_guid)
            invoice.status = self.invoice_model.STATUS_REFUNDING
            transaction = invoice.transactions[0]
            transaction.status = self.transaction_model.STATUS_DONE
            self.session.add(invoice)
            self.session.add(transaction)
            guid = self.transaction_model.create(
                invoice_guid=self.invoice_guid,
                transaction_cls=self.transaction_model.CLS_INVOICE,
                transaction_type=self.transaction_model.TYPE_REFUND,
                amount=invoice.amount,
                scheduled_at=datetime.datetime.utcnow(),
            )

        invoice = self.invoice_model.get(self.invoice_guid)
        transaction = self.transaction_model.get(guid)
        customer = transaction.invoice.customer

        mock_processor = flexmock(
            payout=None,
            charge=None,
        )
        (
            mock_processor 
            .should_receive('create_customer')
            .with_args(customer)
            .replace_with(lambda c: 'AC_MOCK')
            .once()
        )
        (
            mock_processor 
            .should_receive('prepare_customer')
            .with_args(customer, None)
            .replace_with(lambda c, payment_uri: None)
            .once()
        )
        (
            mock_processor 
            .should_receive('refund')
            .with_args(transaction)
            .replace_with(lambda t: 'TX_MOCK')
            .once()
        )

        with freeze_time('2013-08-20'):
            with db_transaction.manager:
                self.transaction_model.process_one(mock_processor, transaction)
                updated_at = datetime.datetime.utcnow()

        transaction = self.transaction_model.get(guid)
        self.assertEqual(transaction.status, self.transaction_model.STATUS_DONE)
        self.assertEqual(transaction.external_id, 'TX_MOCK')
        self.assertEqual(transaction.updated_at, updated_at)
        self.assertEqual(transaction.scheduled_at, now)
        self.assertEqual(transaction.created_at, now)
        self.assertEqual(transaction.invoice.customer.processor_uri, 'AC_MOCK')

        invoice = self.invoice_model.get(self.invoice_guid)
        self.assertEqual(invoice.status, self.invoice_model.STATUS_REFUNDED)

    def test_process_one_with_failure_exceed_limitation(self):
        self._create_records('AC_MOCK')
        payment_uri = '/v1/cards/tester'
        self.transaction_model.maximum_retry = 3

        with db_transaction.manager:
            self.invoice_model.update_payment_uri(self.invoice_guid, payment_uri)

        invoice = self.invoice_model.get(self.invoice_guid)
        transaction = invoice.transactions[0]
        guid = transaction.guid

        def mock_charge(transaction):
            raise RuntimeError('Failed to charge')

        mock_processor = flexmock(
            payout=None,
            refund=None,
        )
        (
            mock_processor 
            .should_receive('prepare_customer')
            .replace_with(lambda c, payment_uri: None)
            .times(4)
        )
        (
            mock_processor 
            .should_receive('charge')
            .replace_with(mock_charge)
            .times(4)
        )

        for _ in range(3):
            with db_transaction.manager:
                transaction = self.transaction_model.get(guid)
                self.transaction_model.process_one(
                    processor=mock_processor, 
                    transaction=transaction, 
                )
            transaction = self.transaction_model.get(guid)
            self.assertEqual(transaction.status, 
                             self.transaction_model.STATUS_RETRYING)
            invoice = self.invoice_model.get(self.invoice_guid)
            self.assertEqual(invoice.status, 
                             self.invoice_model.STATUS_PROCESSING)
        with db_transaction.manager:
            transaction = self.transaction_model.get(guid)
            self.transaction_model.process_one(
                processor=mock_processor, 
                transaction=transaction, 
            )
        transaction = self.transaction_model.get(guid)
        self.assertEqual(transaction.status, 
                         self.transaction_model.STATUS_FAILED)
        invoice = self.invoice_model.get(self.invoice_guid)
        self.assertEqual(invoice.status, 
                         self.invoice_model.STATUS_PROCESS_FAILED)
