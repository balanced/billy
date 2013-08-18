from __future__ import unicode_literals
import datetime

import transaction as db_transaction
from freezegun import freeze_time

from billy.tests.helper import ModelTestCase


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
            self.company_guid = self.company_model.create_company('my_secret_key')
            self.plan_guid = self.plan_model.create_plan(
                company_guid=self.company_guid,
                plan_type=self.plan_model.TYPE_CHARGE,
                amount=10,
                frequency=self.plan_model.FREQ_MONTHLY,
            )
            self.customer_guid = self.customer_model.create_customer(
                company_guid=self.company_guid,
                payment_uri='/v1/credit_card/tester',
            )
            self.subscription_guid = self.subscription_model.create_subscription(
                customer_guid=self.customer_guid,
                plan_guid=self.plan_guid,
            )

    def make_one(self, *args, **kwargs):
        from billy.models.transaction import TransactionModel
        return TransactionModel(*args, **kwargs)

    def test_get_transaction(self):
        model = self.make_one(self.session)

        transaction = model.get_transaction_by_guid('TX_NON_EXIST')
        self.assertEqual(transaction, None)

        with self.assertRaises(KeyError):
            model.get_transaction_by_guid('TX_NON_EXIST', raise_error=True)

        with db_transaction.manager:
            guid = model.create_transaction(
                subscription_guid=self.subscription_guid,
                transaction_type=model.TYPE_CHARGE,
                amount=10,
                payment_uri='/v1/credit_card/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )

        transaction = model.get_transaction_by_guid(guid, raise_error=True)
        self.assertEqual(transaction.guid, guid)

    def test_create_transaction(self):
        model = self.make_one(self.session)

        subscription_guid = self.subscription_guid
        transaction_type = model.TYPE_CHARGE
        amount = 100
        payment_uri = '/v1/credit_card/tester'
        now = datetime.datetime.utcnow()
        scheduled_at = now + datetime.timedelta(days=1)

        with db_transaction.manager:
            guid = model.create_transaction(
                subscription_guid=subscription_guid,
                transaction_type=transaction_type,
                amount=amount,
                payment_uri=payment_uri,
                scheduled_at=scheduled_at,
            )

        transaction = model.get_transaction_by_guid(guid)
        self.assertEqual(transaction.guid, guid)
        self.assert_(transaction.guid.startswith('TX'))
        self.assertEqual(transaction.subscription_guid, subscription_guid)
        self.assertEqual(transaction.transaction_type, transaction_type)
        self.assertEqual(transaction.amount, amount)
        self.assertEqual(transaction.payment_uri, payment_uri)
        self.assertEqual(transaction.status, model.STATUS_INIT)
        self.assertEqual(transaction.scheduled_at, scheduled_at)
        self.assertEqual(transaction.created_at, now)
        self.assertEqual(transaction.updated_at, now)

    def test_create_transaction_with_wrong_type(self):
        model = self.make_one(self.session)

        with self.assertRaises(ValueError):
            model.create_transaction(
                subscription_guid=self.subscription_guid,
                transaction_type=999,
                amount=123,
                payment_uri='/v1/credit_card/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )

    def test_update_transaction(self):
        model = self.make_one(self.session)

        with db_transaction.manager:
            guid = model.create_transaction(
                subscription_guid=self.subscription_guid,
                transaction_type=model.TYPE_CHARGE,
                amount=10,
                payment_uri='/v1/credit_card/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )

        transaction = model.get_transaction_by_guid(guid)
        status = model.STATUS_DONE

        with db_transaction.manager:
            model.update_transaction(
                guid=guid,
                status=status,
            )

        transaction = model.get_transaction_by_guid(guid)
        self.assertEqual(transaction.status, status)

    def test_update_transaction_updated_at(self):
        model = self.make_one(self.session)

        with db_transaction.manager:
            guid = model.create_transaction(
                subscription_guid=self.subscription_guid,
                transaction_type=model.TYPE_CHARGE,
                amount=10,
                payment_uri='/v1/credit_card/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )

        transaction = model.get_transaction_by_guid(guid)
        created_at = transaction.created_at

        # advanced the current date time
        with freeze_time('2013-08-16 07:00:01'):
            with db_transaction.manager:
                model.update_transaction(guid=guid)
            updated_at = datetime.datetime.utcnow()

        transaction = model.get_transaction_by_guid(guid)
        self.assertEqual(transaction.updated_at, updated_at)
        self.assertEqual(transaction.created_at, created_at)

        # advanced the current date time even more
        with freeze_time('2013-08-16 08:35:40'):
            # this should update the updated_at field only
            with db_transaction.manager:
                model.update_transaction(guid)
            updated_at = datetime.datetime.utcnow()

        transaction = model.get_transaction_by_guid(guid)
        self.assertEqual(transaction.updated_at, updated_at)
        self.assertEqual(transaction.created_at, created_at)

    def test_update_transaction_with_wrong_args(self):
        model = self.make_one(self.session)

        with db_transaction.manager:
            guid = model.create_transaction(
                subscription_guid=self.subscription_guid,
                transaction_type=model.TYPE_CHARGE,
                amount=10,
                payment_uri='/v1/credit_card/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )

        # make sure passing wrong argument will raise error
        with self.assertRaises(TypeError):
            model.update_transaction(
                guid=guid, 
                wrong_arg=True, 
                status=model.STATUS_INIT
            )

    def test_update_transaction_with_wrong_status(self):
        model = self.make_one(self.session)

        with db_transaction.manager:
            guid = model.create_transaction(
                subscription_guid=self.subscription_guid,
                transaction_type=model.TYPE_CHARGE,
                amount=10,
                payment_uri='/v1/credit_card/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )

        with self.assertRaises(ValueError):
            model.update_transaction(
                guid=guid,
                status=999,
            )
