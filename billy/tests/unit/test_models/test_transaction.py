from __future__ import unicode_literals
import datetime
import decimal

import transaction as db_transaction
from flexmock import flexmock
from freezegun import freeze_time

from billy.tests.unit.helper import ModelTestCase


@freeze_time('2013-08-16')
class TestTransactionModel(ModelTestCase):

    def setUp(self):
        from billy.models.company import CompanyModel
        from billy.models.customer import CustomerModel
        from billy.models.plan import PlanModel
        from billy.models.subscription import SubscriptionModel
        super(TestTransactionModel, self).setUp()
        # build the basic scenario for transaction model
        self.company_model = CompanyModel(self.session)
        self.customer_model = CustomerModel(self.session)
        self.plan_model = PlanModel(self.session)
        self.subscription_model = SubscriptionModel(self.session)
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
                payment_uri='/v1/cards/tester',
            )

    def make_one(self, *args, **kwargs):
        from billy.models.transaction import TransactionModel
        return TransactionModel(*args, **kwargs)

    def test_get_transaction(self):
        model = self.make_one(self.session)

        transaction = model.get('TX_NON_EXIST')
        self.assertEqual(transaction, None)

        with self.assertRaises(KeyError):
            model.get('TX_NON_EXIST', raise_error=True)

        with db_transaction.manager:
            guid = model.create(
                subscription_guid=self.subscription_guid,
                transaction_type=model.TYPE_CHARGE,
                amount=10,
                payment_uri='/v1/cards/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )

        transaction = model.get(guid, raise_error=True)
        self.assertEqual(transaction.guid, guid)

    def test_create(self):
        model = self.make_one(self.session)

        subscription_guid = self.subscription_guid
        transaction_type = model.TYPE_CHARGE
        amount = 100
        payment_uri = '/v1/cards/tester'
        now = datetime.datetime.utcnow()
        scheduled_at = now + datetime.timedelta(days=1)

        with db_transaction.manager:
            guid = model.create(
                subscription_guid=subscription_guid,
                transaction_type=transaction_type,
                amount=amount,
                payment_uri=payment_uri,
                scheduled_at=scheduled_at,
            )

        transaction = model.get(guid)
        self.assertEqual(transaction.guid, guid)
        self.assert_(transaction.guid.startswith('TX'))
        self.assertEqual(transaction.subscription_guid, subscription_guid)
        self.assertEqual(transaction.transaction_type, transaction_type)
        self.assertEqual(transaction.amount, amount)
        self.assertEqual(transaction.payment_uri, payment_uri)
        self.assertEqual(transaction.status, model.STATUS_INIT)
        self.assertEqual(transaction.failure_count, 0)
        self.assertEqual(transaction.error_message, None)
        self.assertEqual(transaction.scheduled_at, scheduled_at)
        self.assertEqual(transaction.created_at, now)
        self.assertEqual(transaction.updated_at, now)

    def test_create_refund(self):
        model = self.make_one(self.session)

        now = datetime.datetime.utcnow()

        with db_transaction.manager:
            tx_guid = model.create(
                subscription_guid=self.subscription_guid,
                transaction_type=model.TYPE_CHARGE,
                amount=100,
                payment_uri='/v1/cards/tester',
                scheduled_at=now,
            )

        with db_transaction.manager:
            refund_guid = model.create(
                subscription_guid=self.subscription_guid,
                transaction_type=model.TYPE_REFUND,
                refund_to_guid=tx_guid, 
                amount=50,
                scheduled_at=now,
            )

        refund_transaction = model.get(refund_guid)
        self.assertEqual(refund_transaction.refund_to_guid, tx_guid)
        self.assertEqual(refund_transaction.refund_to.guid, tx_guid)
        self.assertEqual(refund_transaction.refund_to.refund_from.guid, 
                         refund_guid)
        self.assertEqual(refund_transaction.transaction_type, model.TYPE_REFUND)
        self.assertEqual(refund_transaction.amount, decimal.Decimal(50))

    def test_create_refund_with_non_exist_target(self):
        model = self.make_one(self.session)
        now = datetime.datetime.utcnow()

        with self.assertRaises(KeyError):
            model.create(
                subscription_guid=self.subscription_guid,
                transaction_type=model.TYPE_REFUND,
                refund_to_guid='TX_NON_EXIST', 
                amount=50,
                scheduled_at=now,
            )

    def test_create_refund_with_wrong_transaction_type(self):
        model = self.make_one(self.session)
        now = datetime.datetime.utcnow()

        with self.assertRaises(ValueError):
            tx_guid = model.create(
                subscription_guid=self.subscription_guid,
                transaction_type=model.TYPE_CHARGE,
                amount=100,
                payment_uri='/v1/cards/tester',
                scheduled_at=now,
            )
            model.create(
                subscription_guid=self.subscription_guid,
                transaction_type=model.TYPE_PAYOUT,
                refund_to_guid=tx_guid, 
                amount=50,
                scheduled_at=now,
            )

    def test_create_refund_with_payment_uri(self):
        model = self.make_one(self.session)
        now = datetime.datetime.utcnow()

        with self.assertRaises(ValueError):
            tx_guid = model.create(
                subscription_guid=self.subscription_guid,
                transaction_type=model.TYPE_CHARGE,
                amount=100,
                payment_uri='/v1/cards/tester',
                scheduled_at=now,
            )
            model.create(
                subscription_guid=self.subscription_guid,
                transaction_type=model.TYPE_REFUND,
                refund_to_guid=tx_guid, 
                amount=50,
                scheduled_at=now,
                payment_uri='/v1/cards/tester',
            )

    def test_create_refund_with_wrong_target(self):
        model = self.make_one(self.session)
        now = datetime.datetime.utcnow()

        with db_transaction.manager:
            tx_guid = model.create(
                subscription_guid=self.subscription_guid,
                transaction_type=model.TYPE_CHARGE,
                amount=100,
                payment_uri='/v1/cards/tester',
                scheduled_at=now,
            )
            refund_guid = model.create(
                subscription_guid=self.subscription_guid,
                transaction_type=model.TYPE_REFUND,
                refund_to_guid=tx_guid, 
                amount=50,
                scheduled_at=now,
            )

        with self.assertRaises(ValueError):
            model.create(
                subscription_guid=self.subscription_guid,
                transaction_type=model.TYPE_REFUND,
                refund_to_guid=refund_guid, 
                amount=50,
                scheduled_at=now,
            )

    def test_create_with_wrong_type(self):
        model = self.make_one(self.session)

        with self.assertRaises(ValueError):
            model.create(
                subscription_guid=self.subscription_guid,
                transaction_type=999,
                amount=123,
                payment_uri='/v1/cards/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )

    def test_update(self):
        model = self.make_one(self.session)

        with db_transaction.manager:
            guid = model.create(
                subscription_guid=self.subscription_guid,
                transaction_type=model.TYPE_CHARGE,
                amount=10,
                payment_uri='/v1/cards/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )

        transaction = model.get(guid)
        status = model.STATUS_DONE

        with db_transaction.manager:
            model.update(
                guid=guid,
                status=status,
            )

        transaction = model.get(guid)
        self.assertEqual(transaction.status, status)

    def test_update_updated_at(self):
        model = self.make_one(self.session)

        with db_transaction.manager:
            guid = model.create(
                subscription_guid=self.subscription_guid,
                transaction_type=model.TYPE_CHARGE,
                amount=10,
                payment_uri='/v1/cards/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )

        transaction = model.get(guid)
        created_at = transaction.created_at

        # advanced the current date time
        with freeze_time('2013-08-16 07:00:01'):
            with db_transaction.manager:
                model.update(guid=guid)
            updated_at = datetime.datetime.utcnow()

        transaction = model.get(guid)
        self.assertEqual(transaction.updated_at, updated_at)
        self.assertEqual(transaction.created_at, created_at)

        # advanced the current date time even more
        with freeze_time('2013-08-16 08:35:40'):
            # this should update the updated_at field only
            with db_transaction.manager:
                model.update(guid)
            updated_at = datetime.datetime.utcnow()

        transaction = model.get(guid)
        self.assertEqual(transaction.updated_at, updated_at)
        self.assertEqual(transaction.created_at, created_at)

    def test_update_with_wrong_args(self):
        model = self.make_one(self.session)

        with db_transaction.manager:
            guid = model.create(
                subscription_guid=self.subscription_guid,
                transaction_type=model.TYPE_CHARGE,
                amount=10,
                payment_uri='/v1/cards/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )

        # make sure passing wrong argument will raise error
        with self.assertRaises(TypeError):
            model.update(
                guid=guid, 
                wrong_arg=True, 
                status=model.STATUS_INIT
            )

    def test_update_with_wrong_status(self):
        model = self.make_one(self.session)

        with db_transaction.manager:
            guid = model.create(
                subscription_guid=self.subscription_guid,
                transaction_type=model.TYPE_CHARGE,
                amount=10,
                payment_uri='/v1/cards/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )

        with self.assertRaises(ValueError):
            model.update(
                guid=guid,
                status=999,
            )

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

    def test_process_one_charge(self):
        model = self.make_one(self.session)
        now = datetime.datetime.utcnow()

        payment_uri = '/v1/cards/tester'

        with db_transaction.manager:
            guid = model.create(
                subscription_guid=self.subscription_guid,
                transaction_type=model.TYPE_CHARGE,
                amount=100,
                payment_uri=payment_uri,
                scheduled_at=now,
            )

        transaction = model.get(guid)
        customer = transaction.subscription.customer

        mock_processor = flexmock()
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
                model.process_one(mock_processor, transaction)
                updated_at = datetime.datetime.utcnow()

        transaction = model.get(guid)
        self.assertEqual(transaction.status, model.STATUS_DONE)
        self.assertEqual(transaction.external_id, 'TX_MOCK')
        self.assertEqual(transaction.updated_at, updated_at)
        self.assertEqual(transaction.scheduled_at, now)
        self.assertEqual(transaction.created_at, now)
        self.assertEqual(transaction.subscription.customer.external_id, 
                         'AC_MOCK')

    def test_process_one_payout(self):
        model = self.make_one(self.session)
        now = datetime.datetime.utcnow()

        payment_uri = '/v1/cards/tester'

        with db_transaction.manager:
            guid = model.create(
                subscription_guid=self.subscription_guid,
                transaction_type=model.TYPE_PAYOUT,
                amount=100,
                payment_uri=payment_uri,
                scheduled_at=now,
            )

        transaction = model.get(guid)
        customer = transaction.subscription.customer

        mock_processor = flexmock()
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
                model.process_one(mock_processor, transaction)
                updated_at = datetime.datetime.utcnow()

        transaction = model.get(guid)
        self.assertEqual(transaction.status, model.STATUS_DONE)
        self.assertEqual(transaction.external_id, 'TX_MOCK')
        self.assertEqual(transaction.updated_at, updated_at)
        self.assertEqual(transaction.scheduled_at, now)
        self.assertEqual(transaction.created_at, now)
        self.assertEqual(transaction.subscription.customer.external_id, 
                         'AC_MOCK')

    def test_process_one_with_failure(self):
        model = self.make_one(self.session)
        now = datetime.datetime.utcnow()

        payment_uri = '/v1/cards/tester'

        with db_transaction.manager:
            guid = model.create(
                subscription_guid=self.subscription_guid,
                transaction_type=model.TYPE_CHARGE,
                amount=100,
                payment_uri=payment_uri,
                scheduled_at=now,
            )

        transaction = model.get(guid)
        customer = transaction.subscription.customer

        def mock_charge(transaction):
            raise RuntimeError('Failed to charge')

        mock_processor = flexmock()
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
            model.process_one(mock_processor, transaction)
            updated_at = datetime.datetime.utcnow()

        transaction = model.get(guid)
        self.assertEqual(transaction.status, model.STATUS_RETRYING)
        self.assertEqual(transaction.updated_at, updated_at)
        self.assertEqual(transaction.failure_count, 1)
        self.assertEqual(transaction.error_message, 'Failed to charge')
        self.assertEqual(transaction.subscription.customer.external_id, 
                         'AC_MOCK')

    def test_process_one_with_system_exit_and_keyboard_interrupt(self):
        model = self.make_one(self.session)
        now = datetime.datetime.utcnow()

        payment_uri = '/v1/cards/tester'

        with db_transaction.manager:
            guid = model.create(
                subscription_guid=self.subscription_guid,
                transaction_type=model.TYPE_CHARGE,
                amount=100,
                payment_uri=payment_uri,
                scheduled_at=now,
            )

        transaction = model.get(guid)

        def mock_create_customer_system_exit(transaction):
            raise SystemExit

        mock_processor = flexmock()
        (
            mock_processor 
            .should_receive('create_customer')
            .replace_with(mock_create_customer_system_exit)
        )

        with self.assertRaises(SystemExit):
            model.process_one(mock_processor, transaction)

        def mock_create_customer_keyboard_interrupt(transaction):
            raise KeyboardInterrupt

        mock_processor = flexmock()
        (
            mock_processor 
            .should_receive('create_customer')
            .replace_with(mock_create_customer_keyboard_interrupt)
        )

        with self.assertRaises(KeyboardInterrupt):
            model.process_one(mock_processor, transaction)

    def test_process_one_with_already_done(self):
        model = self.make_one(self.session)
        now = datetime.datetime.utcnow()

        payment_uri = '/v1/cards/tester'

        with db_transaction.manager:
            guid = model.create(
                subscription_guid=self.subscription_guid,
                transaction_type=model.TYPE_CHARGE,
                amount=100,
                payment_uri=payment_uri,
                scheduled_at=now,
            )
            transaction = model.get(guid)
            transaction.status = model.STATUS_DONE
            self.session.add(transaction)

        processor = flexmock()
        transaction = model.get(guid)
        with self.assertRaises(ValueError):
            model.process_one(processor, transaction)

    def test_process_transactions(self):
        model = self.make_one(self.session)
        now = datetime.datetime.utcnow()

        payment_uri = '/v1/cards/tester'

        with db_transaction.manager:
            guid1 = model.create(
                subscription_guid=self.subscription_guid,
                transaction_type=model.TYPE_CHARGE,
                amount=100,
                payment_uri=payment_uri,
                scheduled_at=now,
            )

            guid2 = model.create(
                subscription_guid=self.subscription_guid,
                transaction_type=model.TYPE_CHARGE,
                amount=100,
                payment_uri=payment_uri,
                scheduled_at=now,
            )
            model.update(guid2, status=model.STATUS_RETRYING)

            guid3 = model.create(
                subscription_guid=self.subscription_guid,
                transaction_type=model.TYPE_CHARGE,
                amount=100,
                payment_uri=payment_uri,
                scheduled_at=now,
            )
            
            guid4 = model.create(
                subscription_guid=self.subscription_guid,
                transaction_type=model.TYPE_CHARGE,
                amount=100,
                payment_uri=payment_uri,
                scheduled_at=now,
            )
            model.update(guid4, status=model.STATUS_DONE)

        processor = flexmock()
        with db_transaction.manager:
            tx_guids = model.process_transactions(processor)

        self.assertEqual(set(tx_guids), set([guid1, guid2, guid3]))
