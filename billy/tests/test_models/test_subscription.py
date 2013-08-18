from __future__ import unicode_literals
import datetime

import transaction as db_transaction
from freezegun import freeze_time

from billy.tests.helper import ModelTestCase


@freeze_time('2013-08-16')
class TestSubscriptionModel(ModelTestCase):

    def setUp(self):
        from billy.models.company import CompanyModel
        from billy.models.customer import CustomerModel
        from billy.models.plan import PlanModel
        super(TestSubscriptionModel, self).setUp()
        # build the basic scenario for plan model
        self.company_model = CompanyModel(self.session)
        self.customer_model = CustomerModel(self.session)
        self.plan_model = PlanModel(self.session)
        with db_transaction.manager:
            self.company_guid = self.company_model.create_company('my_secret_key')
            self.daily_plan_guid = self.plan_model.create_plan(
                company_guid=self.company_guid,
                plan_type=self.plan_model.TYPE_CHARGE,
                amount=10,
                frequency=self.plan_model.FREQ_DAILY,
            )
            self.weekly_plan_guid = self.plan_model.create_plan(
                company_guid=self.company_guid,
                plan_type=self.plan_model.TYPE_CHARGE,
                amount=10,
                frequency=self.plan_model.FREQ_WEEKLY,
            )
            self.monthly_plan_guid = self.plan_model.create_plan(
                company_guid=self.company_guid,
                plan_type=self.plan_model.TYPE_CHARGE,
                amount=10,
                frequency=self.plan_model.FREQ_MONTHLY,
            )
            self.customer_tom_guid = self.customer_model.create_customer(
                company_guid=self.company_guid,
                payment_uri='/v1/credit_card/tom',
            )

    def make_one(self, *args, **kwargs):
        from billy.models.subscription import SubscriptionModel
        return SubscriptionModel(*args, **kwargs)

    def test_get_subscription(self):
        model = self.make_one(self.session)

        subscription = model.get_subscription_by_guid('SU_NON_EXIST')
        self.assertEqual(subscription, None)

        with self.assertRaises(KeyError):
            model.get_subscription_by_guid('SU_NON_EXIST', raise_error=True)

        with db_transaction.manager:
            guid = model.create_subscription(
                customer_guid=self.customer_tom_guid,
                plan_guid=self.monthly_plan_guid,
            )

        subscription = model.get_subscription_by_guid(guid, raise_error=True)
        self.assertEqual(subscription.guid, guid)

    def test_create_subscription(self):
        model = self.make_one(self.session)
        discount = 0.8
        external_id = '5566_GOOD_BROTHERS'
        customer_guid = self.customer_tom_guid
        plan_guid = self.monthly_plan_guid

        with db_transaction.manager:
            guid = model.create_subscription(
                customer_guid=customer_guid,
                plan_guid=plan_guid,
                discount=discount,
                external_id=external_id,
            )

        now = datetime.datetime.utcnow()

        subscription = model.get_subscription_by_guid(guid)
        self.assertEqual(subscription.guid, guid)
        self.assert_(subscription.guid.startswith('SU'))
        self.assertEqual(subscription.customer_guid, customer_guid)
        self.assertEqual(subscription.plan_guid, plan_guid)
        self.assertEqual(subscription.discount, discount)
        self.assertEqual(subscription.external_id, external_id)
        self.assertEqual(subscription.period, 0)
        self.assertEqual(subscription.canceled, False)
        self.assertEqual(subscription.canceled_at, None)
        self.assertEqual(subscription.started_at, now)
        self.assertEqual(subscription.next_transaction_at, now)
        self.assertEqual(subscription.created_at, now)
        self.assertEqual(subscription.updated_at, now)

    def test_create_subscription_with_started_at(self):
        model = self.make_one(self.session)
        customer_guid = self.customer_tom_guid
        plan_guid = self.monthly_plan_guid
        started_at = datetime.datetime.utcnow() + datetime.timedelta(days=1)

        with db_transaction.manager:
            guid = model.create_subscription(
                customer_guid=customer_guid,
                plan_guid=plan_guid,
                started_at=started_at
            )

        subscription = model.get_subscription_by_guid(guid)
        self.assertEqual(subscription.guid, guid)
        self.assertEqual(subscription.started_at, started_at)

    def test_create_subscription_with_negtive_discount(self):
        model = self.make_one(self.session)

        with self.assertRaises(ValueError):
            with db_transaction.manager:
                model.create_subscription(
                    customer_guid=self.customer_tom_guid,
                    plan_guid=self.monthly_plan_guid,
                    discount=-0.1,
                )

    def test_update_subscription(self):
        model = self.make_one(self.session)

        with db_transaction.manager:
            guid = model.create_subscription(
                customer_guid=self.customer_tom_guid,
                plan_guid=self.monthly_plan_guid,
                discount=0.1,
                external_id='old external id'
            )

        subscription = model.get_subscription_by_guid(guid)
        discount = 0.3
        external_id = 'new external id'

        with db_transaction.manager:
            model.update_subscription(
                guid=guid,
                discount=discount,
                external_id=external_id,
            )

        subscription = model.get_subscription_by_guid(guid)
        self.assertEqual(subscription.discount, discount)
        self.assertEqual(subscription.external_id, external_id)

    def test_update_subscription_updated_at(self):
        model = self.make_one(self.session)

        with db_transaction.manager:
            guid = model.create_subscription(
                customer_guid=self.customer_tom_guid,
                plan_guid=self.monthly_plan_guid,
            )

        subscription = model.get_subscription_by_guid(guid)
        created_at = subscription.created_at

        # advanced the current date time
        with freeze_time('2013-08-16 07:00:01'):
            with db_transaction.manager:
                model.update_subscription(guid=guid)
            updated_at = datetime.datetime.utcnow()

        subscription = model.get_subscription_by_guid(guid)
        self.assertEqual(subscription.canceled_at, None)
        self.assertEqual(subscription.updated_at, updated_at)
        self.assertEqual(subscription.created_at, created_at)

        # advanced the current date time even more
        with freeze_time('2013-08-16 08:35:40'):
            # this should update the updated_at field only
            with db_transaction.manager:
                model.update_subscription(guid)
            updated_at = datetime.datetime.utcnow()

        subscription = model.get_subscription_by_guid(guid)
        self.assertEqual(subscription.canceled_at, None)
        self.assertEqual(subscription.updated_at, updated_at)
        self.assertEqual(subscription.created_at, created_at)

    def test_update_subscription_with_wrong_args(self):
        model = self.make_one(self.session)
        with db_transaction.manager:
            guid = model.create_subscription(
                customer_guid=self.customer_tom_guid,
                plan_guid=self.monthly_plan_guid,
            )
        # make sure passing wrong argument will raise error
        with self.assertRaises(TypeError):
            model.update_subscription(guid, wrong_arg=True, neme='john')

    def test_subscription_cancel(self):
        model = self.make_one(self.session)

        with db_transaction.manager:
            guid = model.create_subscription(
                customer_guid=self.customer_tom_guid,
                plan_guid=self.monthly_plan_guid,
            )
            model.cancel_subscription(guid)

        now = datetime.datetime.utcnow()

        subscription = model.get_subscription_by_guid(guid)
        self.assertEqual(subscription.canceled, True)
        self.assertEqual(subscription.canceled_at, now)

    def test_subscription_cancel_with_prorated_refund(self):
        model = self.make_one(self.session)

        with db_transaction.manager:
            model.create_subscription(
                customer_guid=self.customer_tom_guid,
                plan_guid=self.monthly_plan_guid,
            )
        # TODO: check prorated refund here

    def test_subscription_cancel_twice(self):
        from billy.models.subscription import SubscriptionCanceledError
        model = self.make_one(self.session)

        with db_transaction.manager:
            guid = model.create_subscription(
                customer_guid=self.customer_tom_guid,
                plan_guid=self.monthly_plan_guid,
            )
            model.cancel_subscription(guid)

        with self.assertRaises(SubscriptionCanceledError):
            model.cancel_subscription(guid)

    def test_yield_transactions(self):
        from billy.models.transaction import TransactionModel

        now = datetime.datetime.utcnow()

        model = self.make_one(self.session)
        with db_transaction.manager:
            guid = model.create_subscription(
                customer_guid=self.customer_tom_guid,
                plan_guid=self.monthly_plan_guid,
            )
            tx_guids = model.yield_transactions()

        self.assertEqual(len(tx_guids), 1)

        subscription = model.get_subscription_by_guid(guid)
        transactions = subscription.transactions
        self.assertEqual(len(transactions), 1)

        transaction = transactions[0]
        self.assertEqual(transaction.guid, tx_guids[0])
        self.assertEqual(transaction.subscription_guid, guid)
        self.assertEqual(transaction.amount, subscription.plan.amount)
        self.assertEqual(transaction.transaction_type, 
                         TransactionModel.TYPE_CHARGE)
        self.assertEqual(transaction.scheduled_at, now)
        self.assertEqual(transaction.created_at, now)
        self.assertEqual(transaction.updated_at, now)
        self.assertEqual(transaction.status, TransactionModel.STATUS_INIT)
