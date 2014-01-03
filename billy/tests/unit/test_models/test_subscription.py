from __future__ import unicode_literals
import datetime
import contextlib

import transaction as db_transaction
from freezegun import freeze_time

from billy.models.subscription import SubscriptionCanceledError
from billy.tests.unit.helper import ModelTestCase


@freeze_time('2013-08-16')
class TestSubscriptionModel(ModelTestCase):

    def setUp(self):
        super(TestSubscriptionModel, self).setUp()
        # build the basic scenario for plan model
        with db_transaction.manager:
            self.company_guid = self.company_model.create('my_secret_key')
            self.daily_plan_guid = self.plan_model.create(
                company_guid=self.company_guid,
                plan_type=self.plan_model.TYPE_CHARGE,
                amount=1000,  # 10 dollars
                frequency=self.plan_model.FREQ_DAILY,
            )
            self.weekly_plan_guid = self.plan_model.create(
                company_guid=self.company_guid,
                plan_type=self.plan_model.TYPE_CHARGE,
                amount=1000,
                frequency=self.plan_model.FREQ_WEEKLY,
            )
            self.monthly_plan_guid = self.plan_model.create(
                company_guid=self.company_guid,
                plan_type=self.plan_model.TYPE_CHARGE,
                amount=1000,
                frequency=self.plan_model.FREQ_MONTHLY,
            )
            self.customer_tom_guid = self.customer_model.create(
                company_guid=self.company_guid,
            )

    def test_get_subscription(self):
        subscription = self.subscription_model.get('SU_NON_EXIST')
        self.assertEqual(subscription, None)

        with self.assertRaises(KeyError):
            self.subscription_model.get('SU_NON_EXIST', raise_error=True)

        with db_transaction.manager:
            guid = self.subscription_model.create(
                customer_guid=self.customer_tom_guid,
                plan_guid=self.monthly_plan_guid,
            )

        subscription = self.subscription_model.get(guid, raise_error=True)
        self.assertEqual(subscription.guid, guid)

    def test_create(self):
        amount = 5566
        external_id = '5566_GOOD_BROTHERS'
        customer_guid = self.customer_tom_guid
        plan_guid = self.monthly_plan_guid
        funding_instrument_uri = '/v1/credit_cards/id'
        appears_on_statement_as = 'hello baby'

        with db_transaction.manager:
            guid = self.subscription_model.create(
                customer_guid=customer_guid,
                plan_guid=plan_guid,
                amount=amount,
                external_id=external_id,
                funding_instrument_uri=funding_instrument_uri, 
                appears_on_statement_as=appears_on_statement_as, 
            )

        now = datetime.datetime.utcnow()

        subscription = self.subscription_model.get(guid)
        self.assertEqual(subscription.guid, guid)
        self.assert_(subscription.guid.startswith('SU'))
        self.assertEqual(subscription.customer_guid, customer_guid)
        self.assertEqual(subscription.plan_guid, plan_guid)
        self.assertEqual(subscription.amount, amount)
        self.assertEqual(subscription.external_id, external_id)
        self.assertEqual(subscription.funding_instrument_uri, funding_instrument_uri)
        self.assertEqual(subscription.appears_on_statement_as, 
                         appears_on_statement_as)
        self.assertEqual(subscription.period, 0)
        self.assertEqual(subscription.canceled, False)
        self.assertEqual(subscription.canceled_at, None)
        self.assertEqual(subscription.started_at, now)
        self.assertEqual(subscription.next_transaction_at, now)
        self.assertEqual(subscription.created_at, now)
        self.assertEqual(subscription.updated_at, now)

    def test_create_different_created_updated_time(self):
        from billy.models import tables
        results = [
            datetime.datetime(2013, 8, 16, 1),
            datetime.datetime(2013, 8, 16, 2),
        ]

        def mock_utcnow():
            return results.pop(0)

        tables.set_now_func(mock_utcnow)

        with db_transaction.manager:
            guid = self.subscription_model.create(
                customer_guid=self.customer_tom_guid,
                plan_guid=self.monthly_plan_guid,
            )

        subscription = self.subscription_model.get(guid)
        self.assertEqual(subscription.created_at, subscription.updated_at)

    def test_create_with_started_at(self):
        customer_guid = self.customer_tom_guid
        plan_guid = self.monthly_plan_guid
        started_at = datetime.datetime.utcnow() + datetime.timedelta(days=1)

        with db_transaction.manager:
            guid = self.subscription_model.create(
                customer_guid=customer_guid,
                plan_guid=plan_guid,
                started_at=started_at
            )

        subscription = self.subscription_model.get(guid)
        self.assertEqual(subscription.guid, guid)
        self.assertEqual(subscription.started_at, started_at)

    def test_create_with_past_started_at(self):
        started_at = datetime.datetime.utcnow() - datetime.timedelta(days=1)
        with self.assertRaises(ValueError):
            self.subscription_model.create(
                customer_guid=self.customer_tom_guid,
                plan_guid=self.monthly_plan_guid,
                started_at=started_at
            )

    def test_create_with_bad_amount(self):
        with self.assertRaises(ValueError):
            self.subscription_model.create(
                customer_guid=self.customer_tom_guid,
                plan_guid=self.monthly_plan_guid,
                amount=-0.1,
            )
        with self.assertRaises(ValueError):
            self.subscription_model.create(
                customer_guid=self.customer_tom_guid,
                plan_guid=self.monthly_plan_guid,
                amount=0,
            )

    def test_update(self):
        with db_transaction.manager:
            guid = self.subscription_model.create(
                customer_guid=self.customer_tom_guid,
                plan_guid=self.monthly_plan_guid,
                external_id='old external id'
            )

        subscription = self.subscription_model.get(guid)
        external_id = 'new external id'

        with db_transaction.manager:
            self.subscription_model.update(
                guid=guid,
                external_id=external_id,
            )

        subscription = self.subscription_model.get(guid)
        self.assertEqual(subscription.external_id, external_id)

    def test_update_updated_at(self):
        with db_transaction.manager:
            guid = self.subscription_model.create(
                customer_guid=self.customer_tom_guid,
                plan_guid=self.monthly_plan_guid,
            )

        subscription = self.subscription_model.get(guid)
        created_at = subscription.created_at

        # advanced the current date time
        with contextlib.nested(
            freeze_time('2013-08-16 07:00:01'),
            db_transaction.manager,
        ):
            self.subscription_model.update(guid=guid)
            updated_at = datetime.datetime.utcnow()

        subscription = self.subscription_model.get(guid)
        self.assertEqual(subscription.canceled_at, None)
        self.assertEqual(subscription.updated_at, updated_at)
        self.assertEqual(subscription.created_at, created_at)

        # advanced the current date time even more
        with contextlib.nested(
            freeze_time('2013-08-16 08:35:40'),
            db_transaction.manager,
        ):
            # this should update the updated_at field only
            self.subscription_model.update(guid)
            updated_at = datetime.datetime.utcnow()

        subscription = self.subscription_model.get(guid)
        self.assertEqual(subscription.canceled_at, None)
        self.assertEqual(subscription.updated_at, updated_at)
        self.assertEqual(subscription.created_at, created_at)

    def test_update_with_wrong_args(self):
        with db_transaction.manager:
            guid = self.subscription_model.create(
                customer_guid=self.customer_tom_guid,
                plan_guid=self.monthly_plan_guid,
            )
        # make sure passing wrong argument will raise error
        with self.assertRaises(TypeError):
            self.subscription_model.update(guid, wrong_arg=True, neme='john')

    def test_subscription_cancel(self):
        with db_transaction.manager:
            guid = self.subscription_model.create(
                customer_guid=self.customer_tom_guid,
                plan_guid=self.monthly_plan_guid,
            )
            self.subscription_model.cancel(guid)

        now = datetime.datetime.utcnow()

        subscription = self.subscription_model.get(guid)
        self.assertEqual(subscription.canceled, True)
        self.assertEqual(subscription.canceled_at, now)

    def test_subscription_cancel_not_done_transactions(self):
        with db_transaction.manager:
            guid = self.subscription_model.create(
                customer_guid=self.customer_tom_guid,
                plan_guid=self.monthly_plan_guid,
            )

        # okay, 08-16, 09-16, 10-16, 11-16, so we should have 4 new transactions
        # and we assume the transactions status as shown as following:
        # 
        #     [DONE, RETRYING, INIT, FAILED]
        #
        # when we cancel the subscription, the status should be
        # 
        #     [DONE, CANCELED, CANCELED, FAILED]
        #
        init_status = [
            self.transaction_model.STATUS_DONE,
            self.transaction_model.STATUS_RETRYING,
            self.transaction_model.STATUS_INIT,
            self.transaction_model.STATUS_FAILED,
        ]
        with freeze_time('2013-11-16'):
            with db_transaction.manager:
                tx_guids = self.subscription_model.yield_transactions()
                for tx_guid, status in zip(tx_guids, init_status):
                    transaction = self.transaction_model.get(tx_guid)
                    transaction.status = status
                    self.session.add(transaction)
                self.session.add(transaction)
            with db_transaction.manager:
                self.subscription_model.cancel(guid)

        transactions = [self.transaction_model.get(tx_guid) for tx_guid in tx_guids]
        status_list = [tx.status for tx in transactions]
        self.assertEqual(status_list, [
            self.transaction_model.STATUS_DONE, 
            self.transaction_model.STATUS_CANCELED,
            self.transaction_model.STATUS_CANCELED,
            self.transaction_model.STATUS_FAILED,
        ])

    def test_subscription_cancel_with_prorated_refund(self):
        with contextlib.nested(
            freeze_time('2013-06-01'),
            db_transaction.manager,
        ):
            guid = self.subscription_model.create(
                customer_guid=self.customer_tom_guid,
                plan_guid=self.monthly_plan_guid,
            )
            tx_guids = self.subscription_model.yield_transactions()
            transaction = self.transaction_model.get(tx_guids[0])
            transaction.status = self.transaction_model.STATUS_DONE
            transaction.processor_uri = 'MOCK_BALANCED_DEBIT_URI'
            self.session.add(transaction)

        # it is a monthly plan, there is 30 days in June, and only
        # 6 days are elapsed, so 6 / 30 days, the rate should be 1 - 0.2 = 0.8
        # and we have 1000 cent as the amount, we should return 800 to customer
        with contextlib.nested(
            freeze_time('2013-06-07'),
            db_transaction.manager,
        ):
            refund_guid = self.subscription_model.cancel(guid, prorated_refund=True)

        transaction = self.transaction_model.get(refund_guid)
        self.assertEqual(transaction.refund_to_guid, tx_guids[0])
        self.assertEqual(transaction.subscription_guid, guid)
        self.assertEqual(transaction.transaction_type, self.transaction_model.TYPE_REFUND)
        self.assertEqual(transaction.amount, 800)

    def test_subscription_cancel_with_wrong_arguments(self):
        with db_transaction.manager:
            guid = self.subscription_model.create(
                customer_guid=self.customer_tom_guid,
                plan_guid=self.monthly_plan_guid,
            )
            tx_guids = self.subscription_model.yield_transactions()
            transaction = self.transaction_model.get(tx_guids[0])
            transaction.status = self.transaction_model.STATUS_DONE
            transaction.processor_uri = 'MOCK_BALANCED_DEBIT_URI'
            self.session.add(transaction)

        # we should not allow both prorated_refund and refund_amount to 
        # be set
        with self.assertRaises(ValueError):
            self.subscription_model.cancel(guid, prorated_refund=True, refund_amount=10)
        # we should not allow refunding amount that grather than original
        # subscription amount
        with self.assertRaises(ValueError):
            self.subscription_model.cancel(guid, refund_amount=1001)

    def test_subscription_cancel_with_refund_amount(self):
        with db_transaction.manager:
            guid = self.subscription_model.create(
                customer_guid=self.customer_tom_guid,
                plan_guid=self.monthly_plan_guid,
            )
            tx_guids = self.subscription_model.yield_transactions()
            transaction = self.transaction_model.get(tx_guids[0])
            transaction.status = self.transaction_model.STATUS_DONE
            transaction.processor_uri = 'MOCK_BALANCED_DEBIT_URI'
            self.session.add(transaction)

        # let's cancel and refund the latest transaction with amount 566 cent
        with db_transaction.manager:
            refund_guid = self.subscription_model.cancel(
                guid=guid, 
                refund_amount=566,
                appears_on_statement_as='good bye',
            )

        transaction = self.transaction_model.get(refund_guid)
        self.assertEqual(transaction.refund_to_guid, tx_guids[0])
        self.assertEqual(transaction.subscription_guid, guid)
        self.assertEqual(transaction.transaction_type, 
                         self.transaction_model.TYPE_REFUND)
        self.assertEqual(transaction.amount, 566)
        self.assertEqual(transaction.appears_on_statement_as, 'good bye')

    def test_subscription_cancel_with_prorated_refund_and_amount_overwrite(self):
        with contextlib.nested(
            freeze_time('2013-06-01'),
            db_transaction.manager,
        ):
            guid = self.subscription_model.create(
                customer_guid=self.customer_tom_guid,
                plan_guid=self.monthly_plan_guid,
                amount=10000,
            )
            tx_guids = self.subscription_model.yield_transactions()
            transaction = self.transaction_model.get(tx_guids[0])
            transaction.status = self.transaction_model.STATUS_DONE
            transaction.processor_uri = 'MOCK_BALANCED_DEBIT_URI'
            self.session.add(transaction)

        # it is a monthly plan, there is 30 days in June, and only
        # 6 days are elapsed, so 6 / 30 days, the rate should be 1 - 0.2 = 0.8
        # and we have 100 dollars as the amount, we should return 80 dollars to 
        # customer
        with contextlib.nested(
            freeze_time('2013-06-07'),
            db_transaction.manager,
        ):
            refund_guid = self.subscription_model.cancel(
                guid=guid, 
                prorated_refund=True,
                appears_on_statement_as='good bye',
            )

        transaction = self.transaction_model.get(refund_guid)
        self.assertEqual(transaction.amount, 8000)
        self.assertEqual(transaction.appears_on_statement_as, 'good bye')

    def test_subscription_cancel_with_prorated_refund_rounding(self):
        with contextlib.nested(
            freeze_time('2013-06-01'),
            db_transaction.manager,
        ):
            guid = self.subscription_model.create(
                customer_guid=self.customer_tom_guid,
                plan_guid=self.monthly_plan_guid,
            )
            tx_guids = self.subscription_model.yield_transactions()
            transaction = self.transaction_model.get(tx_guids[0])
            transaction.status = self.transaction_model.STATUS_DONE
            transaction.processor_uri = 'MOCK_BALANCED_DEBIT_URI'
            self.session.add(transaction)

        # 17 / 30 days, the rate should be 1 - 0.56666..., which is
        # 0.43333...
        with contextlib.nested(
            freeze_time('2013-06-18'),
            db_transaction.manager,
        ):
                refund_guid = self.subscription_model.cancel(guid, prorated_refund=True)

        transaction = self.transaction_model.get(refund_guid)
        self.assertEqual(transaction.amount, 433)

    def test_subscription_cancel_with_zero_refund(self):
        with contextlib.nested(
            freeze_time('2013-06-01'),
            db_transaction.manager,
        ):
            guid = self.subscription_model.create(
                customer_guid=self.customer_tom_guid,
                plan_guid=self.monthly_plan_guid,
            )
            self.subscription_model.yield_transactions()
        # the subscription period is finished, nothing to refund
        with contextlib.nested(
            freeze_time('2013-07-01'),
            db_transaction.manager,
        ):
            refund_guid = self.subscription_model.cancel(guid, prorated_refund=True)

        self.assertEqual(refund_guid, None)
        subscription = self.subscription_model.get(guid)
        transactions = subscription.transactions
        self.assertEqual(len(transactions), 1)

    def test_subscription_cancel_twice(self):
        with db_transaction.manager:
            guid = self.subscription_model.create(
                customer_guid=self.customer_tom_guid,
                plan_guid=self.monthly_plan_guid,
            )
            self.subscription_model.cancel(guid)

        with self.assertRaises(SubscriptionCanceledError):
            self.subscription_model.cancel(guid)

    def test_yield_transactions(self):
        now = datetime.datetime.utcnow()

        with db_transaction.manager:
            guid = self.subscription_model.create(
                customer_guid=self.customer_tom_guid,
                plan_guid=self.monthly_plan_guid,
            )
            tx_guids = self.subscription_model.yield_transactions()

        self.assertEqual(len(tx_guids), 1)

        subscription = self.subscription_model.get(guid)
        transactions = subscription.transactions
        self.assertEqual(len(transactions), 1)

        transaction = transactions[0]
        self.assertEqual(transaction.guid, tx_guids[0])
        self.assertEqual(transaction.subscription_guid, guid)
        self.assertEqual(transaction.amount, subscription.plan.amount)
        self.assertEqual(transaction.transaction_type, 
                         self.transaction_model.TYPE_CHARGE)
        self.assertEqual(transaction.scheduled_at, now)
        self.assertEqual(transaction.created_at, now)
        self.assertEqual(transaction.updated_at, now)
        self.assertEqual(transaction.status, self.transaction_model.STATUS_INIT)

        # we should not yield new transaction as the datetime is the same
        with db_transaction.manager:
            tx_guids = self.subscription_model.yield_transactions()
        self.assertFalse(tx_guids)
        subscription = self.subscription_model.get(guid)
        self.assertEqual(len(subscription.transactions), 1)

        # should not yield new transaction as 09-16 is the date
        with contextlib.nested(
            freeze_time('2013-09-15'),
            db_transaction.manager,
        ):
                tx_guids = self.subscription_model.yield_transactions()
        self.assertFalse(tx_guids)
        subscription = self.subscription_model.get(guid)
        self.assertEqual(len(subscription.transactions), 1)

        # okay, should yield new transaction now
        with contextlib.nested(
            freeze_time('2013-09-16'),
            db_transaction.manager,
        ):
            tx_guids = self.subscription_model.yield_transactions()
            scheduled_at = datetime.datetime.utcnow()
        self.assertEqual(len(tx_guids), 1)
        subscription = self.subscription_model.get(guid)
        self.assertEqual(len(subscription.transactions), 2)

        transaction = self.transaction_model.get(tx_guids[0])
        self.assertEqual(transaction.subscription_guid, guid)
        self.assertEqual(transaction.amount, subscription.plan.amount)
        self.assertEqual(transaction.transaction_type, 
                         self.transaction_model.TYPE_CHARGE)
        self.assertEqual(transaction.scheduled_at, scheduled_at)
        self.assertEqual(transaction.created_at, scheduled_at)
        self.assertEqual(transaction.updated_at, scheduled_at)
        self.assertEqual(transaction.status, self.transaction_model.STATUS_INIT)

    def test_yield_transactions_for_specific_subscriptions(self):
        with db_transaction.manager:
            guid1 = self.subscription_model.create(
                customer_guid=self.customer_tom_guid,
                plan_guid=self.monthly_plan_guid,
            )
            self.subscription_model.create(
                customer_guid=self.customer_tom_guid,
                plan_guid=self.monthly_plan_guid,
            )
            guid2 = self.subscription_model.create(
                customer_guid=self.customer_tom_guid,
                plan_guid=self.monthly_plan_guid,
            )
            self.subscription_model.create(
                customer_guid=self.customer_tom_guid,
                plan_guid=self.monthly_plan_guid,
            )
            tx_guids = self.subscription_model.yield_transactions([guid1, guid2])

        self.assertEqual(len(tx_guids), 2)
        subscription_guids = [
            self.transaction_model.get(tx_guid).subscription_guid 
            for tx_guid in tx_guids
        ]
        self.assertEqual(set(subscription_guids), set([guid1, guid2]))

    def test_yield_transactions_with_multiple_period(self):
        with db_transaction.manager:
            guid = self.subscription_model.create(
                customer_guid=self.customer_tom_guid,
                plan_guid=self.monthly_plan_guid,
            )

        # okay, 08-16, 09-16, 10-16, so we should have 3 new transactions
        with contextlib.nested(
            freeze_time('2013-10-16'),
            db_transaction.manager,
        ):
            tx_guids = self.subscription_model.yield_transactions()

        self.assertEqual(len(set(tx_guids)), 3)
        subscription = self.subscription_model.get(guid)
        self.assertEqual(len(subscription.transactions), 3)

        sub_tx_guids = [tx.guid for tx in subscription.transactions]
        self.assertEqual(set(tx_guids), set(sub_tx_guids))

        tx_dates = [tx.scheduled_at for tx in subscription.transactions]
        self.assertEqual(set(tx_dates), set([
            datetime.datetime(2013, 8, 16),
            datetime.datetime(2013, 9, 16),
            datetime.datetime(2013, 10, 16),
        ]))

    def test_yield_transactions_with_amount_overwrite(self):
        with db_transaction.manager:
            guid = self.subscription_model.create(
                customer_guid=self.customer_tom_guid,
                plan_guid=self.monthly_plan_guid,
                amount=5566, 
            )

        # okay, 08-16, 09-16, 10-16, so we should have 3 new transactions
        with contextlib.nested(
            freeze_time('2013-10-16'),
            db_transaction.manager,
        ):
            self.subscription_model.yield_transactions()

        subscription = self.subscription_model.get(guid)
        amounts = [tx.amount for tx in subscription.transactions]
        self.assertEqual(amounts, [
            5566,
            5566,
            5566,
        ])

    def test_yield_transactions_with_multiple_interval(self):
        with db_transaction.manager:
            plan_guid = self.plan_model.create(
                company_guid=self.company_guid,
                plan_type=self.plan_model.TYPE_PAYOUT,
                amount=10,
                frequency=self.plan_model.FREQ_MONTHLY,
                interval=2,
            )
            guid = self.subscription_model.create(
                customer_guid=self.customer_tom_guid,
                plan_guid=plan_guid,
            )

        # okay, 08-16, 10-16, so we should have 2 new transactions
        with contextlib.nested(
            freeze_time('2013-10-16'),
            db_transaction.manager,
        ):
            tx_guids = self.subscription_model.yield_transactions()

        self.assertEqual(len(set(tx_guids)), 2)
        subscription = self.subscription_model.get(guid)
        self.assertEqual(len(subscription.transactions), 2)

    def test_yield_transactions_with_payout(self):
        with db_transaction.manager:
            plan_guid = self.plan_model.create(
                company_guid=self.company_guid,
                plan_type=self.plan_model.TYPE_PAYOUT,
                amount=10,
                frequency=self.plan_model.FREQ_MONTHLY,
            )
            guid = self.subscription_model.create(
                customer_guid=self.customer_tom_guid,
                plan_guid=plan_guid,
            )
            self.subscription_model.yield_transactions()

        subscription = self.subscription_model.get(guid)
        transaction = subscription.transactions[0]
        self.assertEqual(transaction.transaction_type, 
                         self.transaction_model.TYPE_PAYOUT)

    def test_yield_transactions_with_started_at(self):
        with db_transaction.manager:
            guid = self.subscription_model.create(
                customer_guid=self.customer_tom_guid,
                plan_guid=self.monthly_plan_guid,
                started_at=datetime.datetime(2013, 9, 1),
            )

        with db_transaction.manager:
            tx_guids = self.subscription_model.yield_transactions()

        self.assertFalse(tx_guids)
        subscription = self.subscription_model.get(guid)
        self.assertFalse(subscription.transactions)

        # 
        with contextlib.nested(
            freeze_time('2013-09-01'),
            db_transaction.manager,
        ):
            tx_guids = self.subscription_model.yield_transactions()

        self.assertEqual(len(set(tx_guids)), 1)
        subscription = self.subscription_model.get(guid)
        self.assertEqual(len(subscription.transactions), 1)

        transaction = subscription.transactions[0]
        self.assertEqual(transaction.scheduled_at, 
                         datetime.datetime(2013, 9, 1))

    def test_yield_transactions_with_wrong_type(self):
        with db_transaction.manager:
            guid = self.subscription_model.create(
                customer_guid=self.customer_tom_guid,
                plan_guid=self.monthly_plan_guid,
            )
            subscription = self.subscription_model.get(guid)
            subscription.plan.plan_type = 999
            self.session.add(subscription.plan)

        with self.assertRaises(ValueError):
            self.subscription_model.yield_transactions()

    def test_yield_transactions_with_canceled_subscription(self):
        with db_transaction.manager:
            guid = self.subscription_model.create(
                customer_guid=self.customer_tom_guid,
                plan_guid=self.monthly_plan_guid,
                started_at=datetime.datetime(2013, 9, 1),
            )
            self.subscription_model.cancel(guid)

        with db_transaction.manager:
            tx_guids = self.subscription_model.yield_transactions()

        self.assertFalse(tx_guids)
        subscription = self.subscription_model.get(guid)
        self.assertFalse(subscription.transactions)

    def test_yield_transactions_with_canceled_in_middle(self):
        with db_transaction.manager:
            guid = self.subscription_model.create(
                customer_guid=self.customer_tom_guid,
                plan_guid=self.monthly_plan_guid,
            )

        # 08-16, 09-16, 10-16 transactions should be yielded
        with contextlib.nested(
            freeze_time('2013-10-16'),
            db_transaction.manager,
        ):
            tx_guids = self.subscription_model.yield_transactions()

        self.assertEqual(len(set(tx_guids)), 3)
        subscription = self.subscription_model.get(guid)
        self.assertEqual(len(subscription.transactions), 3)

        # okay, cancel this, there should be no more new transactions
        with db_transaction.manager:
            self.subscription_model.cancel(guid)

        with contextlib.nested(
            freeze_time('2020-12-31'),
            db_transaction.manager,
        ):
            tx_guids = self.subscription_model.yield_transactions()

        self.assertFalse(tx_guids)
        subscription = self.subscription_model.get(guid)
        self.assertEqual(len(subscription.transactions), 3)

    def test_list_by_company_guid(self):
        # create another company with subscriptions
        with db_transaction.manager:
            other_company_guid = self.company_model.create('my_secret_key')
            other_plan_guid = self.plan_model.create(
                company_guid=other_company_guid,
                plan_type=self.plan_model.TYPE_CHARGE,
                amount=10,
                frequency=self.plan_model.FREQ_MONTHLY,
            )
            other_customer_guid = self.customer_model.create(
                company_guid=other_company_guid,
            )
            guids1 = []
            for i in range(2):
                with freeze_time('2013-08-16 00:00:{:02}'.format(i)):
                    guid = self.subscription_model.create(
                        customer_guid=other_customer_guid,
                        plan_guid=other_plan_guid,
                    )
                    guids1.append(guid)
        with db_transaction.manager:
            guids2 = []
            for i in range(3):
                with freeze_time('2013-08-16 00:00:{:02}'.format(i)):
                    guid = self.subscription_model.create(
                        customer_guid=self.customer_tom_guid,
                        plan_guid=self.monthly_plan_guid,
                    )
                    guids2.append(guid)

        guids1 = list(reversed(guids1))
        guids2 = list(reversed(guids2))

        def assert_list_by_company_guid(
            company_guid, 
            expected, 
            offset=None, 
            limit=None,
        ):
            result = self.subscription_model.list_by_company_guid(
                company_guid, 
                offset=offset, 
                limit=limit,
            )
            result_guids = [s.guid for s in result]
            self.assertEqual(result_guids, expected)

        assert_list_by_company_guid(other_company_guid, guids1)
        assert_list_by_company_guid(other_company_guid, guids1[1:], offset=1)
        assert_list_by_company_guid(other_company_guid, guids1[2:], offset=2)
        assert_list_by_company_guid(other_company_guid, guids1[:1], limit=1)
        assert_list_by_company_guid(self.company_guid, guids2)
