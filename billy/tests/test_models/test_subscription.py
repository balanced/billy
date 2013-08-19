from __future__ import unicode_literals
import datetime
import decimal

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
            self.company_guid = self.company_model.create('my_secret_key')
            self.daily_plan_guid = self.plan_model.create(
                company_guid=self.company_guid,
                plan_type=self.plan_model.TYPE_CHARGE,
                amount=10,
                frequency=self.plan_model.FREQ_DAILY,
            )
            self.weekly_plan_guid = self.plan_model.create(
                company_guid=self.company_guid,
                plan_type=self.plan_model.TYPE_CHARGE,
                amount=10,
                frequency=self.plan_model.FREQ_WEEKLY,
            )
            self.monthly_plan_guid = self.plan_model.create(
                company_guid=self.company_guid,
                plan_type=self.plan_model.TYPE_CHARGE,
                amount=10,
                frequency=self.plan_model.FREQ_MONTHLY,
            )
            self.customer_tom_guid = self.customer_model.create(
                company_guid=self.company_guid,
                payment_uri='/v1/credit_card/tom',
            )

    def make_one(self, *args, **kwargs):
        from billy.models.subscription import SubscriptionModel
        return SubscriptionModel(*args, **kwargs)

    def test_get_subscription(self):
        model = self.make_one(self.session)

        subscription = model.get('SU_NON_EXIST')
        self.assertEqual(subscription, None)

        with self.assertRaises(KeyError):
            model.get('SU_NON_EXIST', raise_error=True)

        with db_transaction.manager:
            guid = model.create(
                customer_guid=self.customer_tom_guid,
                plan_guid=self.monthly_plan_guid,
            )

        subscription = model.get(guid, raise_error=True)
        self.assertEqual(subscription.guid, guid)

    def test_create(self):
        model = self.make_one(self.session)
        discount = decimal.Decimal('0.8')
        external_id = '5566_GOOD_BROTHERS'
        customer_guid = self.customer_tom_guid
        plan_guid = self.monthly_plan_guid

        with db_transaction.manager:
            guid = model.create(
                customer_guid=customer_guid,
                plan_guid=plan_guid,
                discount=discount,
                external_id=external_id,
            )

        now = datetime.datetime.utcnow()

        subscription = model.get(guid)
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

    def test_create_with_started_at(self):
        model = self.make_one(self.session)
        customer_guid = self.customer_tom_guid
        plan_guid = self.monthly_plan_guid
        started_at = datetime.datetime.utcnow() + datetime.timedelta(days=1)

        with db_transaction.manager:
            guid = model.create(
                customer_guid=customer_guid,
                plan_guid=plan_guid,
                started_at=started_at
            )

        subscription = model.get(guid)
        self.assertEqual(subscription.guid, guid)
        self.assertEqual(subscription.started_at, started_at)

    def test_create_with_negtive_discount(self):
        model = self.make_one(self.session)

        with self.assertRaises(ValueError):
            with db_transaction.manager:
                model.create(
                    customer_guid=self.customer_tom_guid,
                    plan_guid=self.monthly_plan_guid,
                    discount=-0.1,
                )

    def test_update(self):
        model = self.make_one(self.session)

        with db_transaction.manager:
            guid = model.create(
                customer_guid=self.customer_tom_guid,
                plan_guid=self.monthly_plan_guid,
                discount=0.1,
                external_id='old external id'
            )

        subscription = model.get(guid)
        discount = decimal.Decimal('0.3')
        external_id = 'new external id'

        with db_transaction.manager:
            model.update(
                guid=guid,
                discount=discount,
                external_id=external_id,
            )

        subscription = model.get(guid)
        self.assertEqual(subscription.discount, discount)
        self.assertEqual(subscription.external_id, external_id)

    def test_update_updated_at(self):
        model = self.make_one(self.session)

        with db_transaction.manager:
            guid = model.create(
                customer_guid=self.customer_tom_guid,
                plan_guid=self.monthly_plan_guid,
            )

        subscription = model.get(guid)
        created_at = subscription.created_at

        # advanced the current date time
        with freeze_time('2013-08-16 07:00:01'):
            with db_transaction.manager:
                model.update(guid=guid)
            updated_at = datetime.datetime.utcnow()

        subscription = model.get(guid)
        self.assertEqual(subscription.canceled_at, None)
        self.assertEqual(subscription.updated_at, updated_at)
        self.assertEqual(subscription.created_at, created_at)

        # advanced the current date time even more
        with freeze_time('2013-08-16 08:35:40'):
            # this should update the updated_at field only
            with db_transaction.manager:
                model.update(guid)
            updated_at = datetime.datetime.utcnow()

        subscription = model.get(guid)
        self.assertEqual(subscription.canceled_at, None)
        self.assertEqual(subscription.updated_at, updated_at)
        self.assertEqual(subscription.created_at, created_at)

    def test_update_with_wrong_args(self):
        model = self.make_one(self.session)
        with db_transaction.manager:
            guid = model.create(
                customer_guid=self.customer_tom_guid,
                plan_guid=self.monthly_plan_guid,
            )
        # make sure passing wrong argument will raise error
        with self.assertRaises(TypeError):
            model.update(guid, wrong_arg=True, neme='john')

    def test_subscription_cancel(self):
        model = self.make_one(self.session)

        with db_transaction.manager:
            guid = model.create(
                customer_guid=self.customer_tom_guid,
                plan_guid=self.monthly_plan_guid,
            )
            model.cancel(guid)

        now = datetime.datetime.utcnow()

        subscription = model.get(guid)
        self.assertEqual(subscription.canceled, True)
        self.assertEqual(subscription.canceled_at, now)

    def test_subscription_cancel_with_prorated_refund(self):
        model = self.make_one(self.session)

        with db_transaction.manager:
            model.create(
                customer_guid=self.customer_tom_guid,
                plan_guid=self.monthly_plan_guid,
            )
        # TODO: check prorated refund here

    def test_subscription_cancel_twice(self):
        from billy.models.subscription import SubscriptionCanceledError
        model = self.make_one(self.session)

        with db_transaction.manager:
            guid = model.create(
                customer_guid=self.customer_tom_guid,
                plan_guid=self.monthly_plan_guid,
            )
            model.cancel(guid)

        with self.assertRaises(SubscriptionCanceledError):
            model.cancel(guid)

    def test_yield_transactions(self):
        from billy.models.transaction import TransactionModel

        model = self.make_one(self.session)
        tx_model = TransactionModel(self.session)

        now = datetime.datetime.utcnow()

        with db_transaction.manager:
            guid = model.create(
                customer_guid=self.customer_tom_guid,
                plan_guid=self.monthly_plan_guid,
            )
            tx_guids = model.yield_transactions()

        self.assertEqual(len(tx_guids), 1)

        subscription = model.get(guid)
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

        # we should not yield new transaction as the datetime is the same
        with db_transaction.manager:
            tx_guids = model.yield_transactions()
        self.assertFalse(tx_guids)
        subscription = model.get(guid)
        self.assertEqual(len(subscription.transactions), 1)

        # should not yield new transaction as 09-16 is the date
        with freeze_time('2013-09-15'):
            with db_transaction.manager:
                tx_guids = model.yield_transactions()
        self.assertFalse(tx_guids)
        subscription = model.get(guid)
        self.assertEqual(len(subscription.transactions), 1)

        # okay, should yield new transaction now
        with freeze_time('2013-09-16'):
            with db_transaction.manager:
                tx_guids = model.yield_transactions()
            scheduled_at = datetime.datetime.utcnow()
        self.assertEqual(len(tx_guids), 1)
        subscription = model.get(guid)
        self.assertEqual(len(subscription.transactions), 2)

        transaction = tx_model.get(tx_guids[0])
        self.assertEqual(transaction.subscription_guid, guid)
        self.assertEqual(transaction.amount, subscription.plan.amount)
        self.assertEqual(transaction.transaction_type, 
                         TransactionModel.TYPE_CHARGE)
        self.assertEqual(transaction.scheduled_at, scheduled_at)
        self.assertEqual(transaction.created_at, scheduled_at)
        self.assertEqual(transaction.updated_at, scheduled_at)
        self.assertEqual(transaction.status, TransactionModel.STATUS_INIT)

    def test_yield_transactions_with_multiple_period(self):
        model = self.make_one(self.session)

        with db_transaction.manager:
            guid = model.create(
                customer_guid=self.customer_tom_guid,
                plan_guid=self.monthly_plan_guid,
            )

        # okay, 08-16, 09-16, 10-16, so we should have 3 new transactions
        with freeze_time('2013-10-16'):
            with db_transaction.manager:
                tx_guids = model.yield_transactions()

        self.assertEqual(len(set(tx_guids)), 3)
        subscription = model.get(guid)
        self.assertEqual(len(subscription.transactions), 3)

        sub_tx_guids = [tx.guid for tx in subscription.transactions]
        self.assertEqual(set(tx_guids), set(sub_tx_guids))

        tx_dates = [tx.scheduled_at for tx in subscription.transactions]
        self.assertEqual(tx_dates, [
            datetime.datetime(2013, 8, 16),
            datetime.datetime(2013, 9, 16),
            datetime.datetime(2013, 10, 16),
        ])

    def test_yield_transactions_with_payout(self):
        from billy.models.transaction import TransactionModel
        model = self.make_one(self.session)

        with db_transaction.manager:
            plan_guid = self.plan_model.create(
                company_guid=self.company_guid,
                plan_type=self.plan_model.TYPE_PAYOUT,
                amount=10,
                frequency=self.plan_model.FREQ_MONTHLY,
            )
            guid = model.create(
                customer_guid=self.customer_tom_guid,
                plan_guid=plan_guid,
            )
            model.yield_transactions()

        subscription = model.get(guid)
        transaction = subscription.transactions[0]
        self.assertEqual(transaction.transaction_type, 
                         TransactionModel.TYPE_PAYOUT)

    def test_yield_transactions_with_started_at(self):
        model = self.make_one(self.session)

        with db_transaction.manager:
            guid = model.create(
                customer_guid=self.customer_tom_guid,
                plan_guid=self.monthly_plan_guid,
                started_at=datetime.datetime(2013, 9, 1),
            )

        with db_transaction.manager:
            tx_guids = model.yield_transactions()

        self.assertFalse(tx_guids)
        subscription = model.get(guid)
        self.assertFalse(subscription.transactions)

        # 
        with freeze_time('2013-09-01'):
            with db_transaction.manager:
                tx_guids = model.yield_transactions()

        self.assertEqual(len(set(tx_guids)), 1)
        subscription = model.get(guid)
        self.assertEqual(len(subscription.transactions), 1)

        transaction = subscription.transactions[0]
        self.assertEqual(transaction.scheduled_at, 
                         datetime.datetime(2013, 9, 1))

    def test_yield_transactions_with_wrong_type(self):
        model = self.make_one(self.session)

        with db_transaction.manager:
            guid = model.create(
                customer_guid=self.customer_tom_guid,
                plan_guid=self.monthly_plan_guid,
            )
            subscription = model.get(guid)
            subscription.plan.plan_type = 999
            self.session.add(subscription.plan)

        with self.assertRaises(ValueError):
            model.yield_transactions()

    def test_yield_transactions_with_canceled_subscription(self):
        model = self.make_one(self.session)

        with db_transaction.manager:
            guid = model.create(
                customer_guid=self.customer_tom_guid,
                plan_guid=self.monthly_plan_guid,
                started_at=datetime.datetime(2013, 9, 1),
            )
            model.cancel(guid)

        tx_guids = model.yield_transactions()
        self.assertFalse(tx_guids)
        subscription = model.get(guid)
        self.assertFalse(subscription.transactions)

    # TODO: test cancel in middle
