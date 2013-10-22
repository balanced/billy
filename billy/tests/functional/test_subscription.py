from __future__ import unicode_literals
import datetime

import transaction as db_transaction
from flexmock import flexmock
from freezegun import freeze_time

from billy.tests.functional.helper import ViewTestCase


class DummyProcessor(object):

    def create_customer(self, customer):
        pass

    def prepare_customer(self, customer, payment_uri=None):
        pass

    def charge(self, transaction):
        pass

    def payout(self, transaction):
        pass

    def refund(self, transaction):
        pass


@freeze_time('2013-08-16')
class TestSubscriptionViews(ViewTestCase):

    def setUp(self):
        from billy.models.company import CompanyModel
        from billy.models.customer import CustomerModel
        from billy.models.plan import PlanModel
        self.settings = {
            'billy.processor_factory': DummyProcessor
        }
        super(TestSubscriptionViews, self).setUp()
        company_model = CompanyModel(self.testapp.session)
        customer_model = CustomerModel(self.testapp.session)
        plan_model = PlanModel(self.testapp.session)
        with db_transaction.manager:
            self.company_guid = company_model.create(
                processor_key='MOCK_PROCESSOR_KEY',
            )
            self.customer_guid = customer_model.create(
                company_guid=self.company_guid
            )
            self.plan_guid = plan_model.create(
                company_guid=self.company_guid,
                frequency=plan_model.FREQ_WEEKLY,
                plan_type=plan_model.TYPE_CHARGE,
                amount=1000,
            )
        company = company_model.get(self.company_guid)
        self.api_key = str(company.api_key)

    def test_create_subscription(self):
        from billy.models.subscription import SubscriptionModel
        from billy.models.transaction import TransactionModel

        customer_guid = self.customer_guid
        plan_guid = self.plan_guid
        amount = 5566
        payment_uri = 'MOCK_CARD_URI'
        now = datetime.datetime.utcnow()
        now_iso = now.isoformat()
        # next week
        next_transaction_at = datetime.datetime(2013, 8, 23)
        next_iso = next_transaction_at.isoformat()

        def mock_charge(transaction):
            self.assertEqual(transaction.subscription.customer_guid, 
                             customer_guid)
            self.assertEqual(transaction.subscription.plan_guid, 
                             plan_guid)
            return 'MOCK_PROCESSOR_TRANSACTION_ID'

        mock_processor = flexmock(DummyProcessor)
        (
            mock_processor
            .should_receive('create_customer')
            .once()
        )

        (
            mock_processor
            .should_receive('charge')
            .replace_with(mock_charge)
            .once()
        )

        res = self.testapp.post(
            '/v1/subscriptions',
            dict(
                customer_guid=customer_guid,
                plan_guid=plan_guid,
                amount=amount,
                payment_uri=payment_uri,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        self.failUnless('guid' in res.json)
        self.assertEqual(res.json['created_at'], now_iso)
        self.assertEqual(res.json['updated_at'], now_iso)
        self.assertEqual(res.json['canceled_at'], None)
        self.assertEqual(res.json['next_transaction_at'], next_iso)
        self.assertEqual(res.json['period'], 1)
        self.assertEqual(res.json['amount'], amount)
        self.assertEqual(res.json['customer_guid'], customer_guid)
        self.assertEqual(res.json['plan_guid'], plan_guid)
        self.assertEqual(res.json['payment_uri'], payment_uri)
        self.assertEqual(res.json['canceled'], False)

        subscription_model = SubscriptionModel(self.testapp.session)
        subscription = subscription_model.get(res.json['guid'])
        self.assertEqual(len(subscription.transactions), 1)
        transaction = subscription.transactions[0]
        self.assertEqual(transaction.external_id, 
                         'MOCK_PROCESSOR_TRANSACTION_ID')
        self.assertEqual(transaction.status, TransactionModel.STATUS_DONE)

    def test_create_subscription_with_default_payment_uri(self):
        from billy.models.subscription import SubscriptionModel
        from billy.models.transaction import TransactionModel

        customer_guid = self.customer_guid
        plan_guid = self.plan_guid
        amount = 5566
        now = datetime.datetime.utcnow()
        now_iso = now.isoformat()
        # next week
        next_transaction_at = datetime.datetime(2013, 8, 23)
        next_iso = next_transaction_at.isoformat()

        def mock_charge(transaction):
            self.assertEqual(transaction.subscription.customer_guid, 
                             customer_guid)
            self.assertEqual(transaction.subscription.plan_guid, 
                             plan_guid)
            return 'MOCK_PROCESSOR_TRANSACTION_ID'

        mock_processor = flexmock(DummyProcessor)
        (
            mock_processor
            .should_receive('create_customer')
            .once()
        )

        (
            mock_processor
            .should_receive('charge')
            .replace_with(mock_charge)
            .once()
        )

        res = self.testapp.post(
            '/v1/subscriptions',
            dict(
                customer_guid=customer_guid,
                plan_guid=plan_guid,
                amount=amount,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        self.failUnless('guid' in res.json)
        self.assertEqual(res.json['created_at'], now_iso)
        self.assertEqual(res.json['updated_at'], now_iso)
        self.assertEqual(res.json['canceled_at'], None)
        self.assertEqual(res.json['next_transaction_at'], next_iso)
        self.assertEqual(res.json['period'], 1)
        self.assertEqual(res.json['amount'], amount)
        self.assertEqual(res.json['customer_guid'], customer_guid)
        self.assertEqual(res.json['plan_guid'], plan_guid)
        self.assertEqual(res.json['payment_uri'], None)
        self.assertEqual(res.json['canceled'], False)

        subscription_model = SubscriptionModel(self.testapp.session)
        subscription = subscription_model.get(res.json['guid'])
        self.assertEqual(len(subscription.transactions), 1)
        transaction = subscription.transactions[0]
        self.assertEqual(transaction.external_id, 
                         'MOCK_PROCESSOR_TRANSACTION_ID')
        self.assertEqual(transaction.status, TransactionModel.STATUS_DONE)

    def test_create_subscription_to_a_deleted_plan(self):
        from billy.models.plan import PlanModel

        plan_model = PlanModel(self.testapp.session)

        with db_transaction.manager:
            plan_guid = plan_model.create(
                company_guid=self.company_guid,
                frequency=plan_model.FREQ_WEEKLY,
                plan_type=plan_model.TYPE_CHARGE,
                amount=10,
            )
            plan_model.delete(plan_guid)

        self.testapp.post(
            '/v1/subscriptions',
            dict(
                customer_guid=self.customer_guid,
                plan_guid=plan_guid,
                amount='123',
                payment_uri='MOCK_CARD_URI',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=400,
        )

    def test_create_subscription_to_a_deleted_customer(self):
        from billy.models.customer import CustomerModel

        customer_model = CustomerModel(self.testapp.session)

        with db_transaction.manager:
            customer_guid = customer_model.create(
                company_guid=self.company_guid
            )
            customer_model.delete(customer_guid)

        self.testapp.post(
            '/v1/subscriptions',
            dict(
                customer_guid=customer_guid,
                plan_guid=self.plan_guid,
                amount='123',
                payment_uri='MOCK_CARD_URI',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=400,
        )

    def test_create_subscription_with_none_amount(self):
        res = self.testapp.post(
            '/v1/subscriptions',
            dict(
                customer_guid=self.customer_guid,
                plan_guid=self.plan_guid,
                payment_uri='MOCK_CARD_URI',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        self.assertEqual(res.json['amount'], None)

    def test_create_subscription_with_past_started_at(self):
        self.testapp.post(
            '/v1/subscriptions',
            dict(
                customer_guid=self.customer_guid,
                plan_guid=self.plan_guid,
                started_at='2013-08-15T23:59:59Z',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=400,
        )

    def test_create_subscription_with_bad_parameters(self):
        def assert_bad_parameters(params):
            self.testapp.post(
                '/v1/subscriptions',
                params, 
                extra_environ=dict(REMOTE_USER=self.api_key), 
                status=400,
            )
        assert_bad_parameters({})
        assert_bad_parameters(dict(customer_guid=self.customer_guid))
        assert_bad_parameters(dict(
            customer_guid=self.customer_guid,
            plan_guid=self.plan_guid,
            amount='BAD_AMOUNT',
        ))
        assert_bad_parameters(dict(
            customer_guid=self.customer_guid,
            plan_guid=self.plan_guid,
            amount='-123.45',
        ))
        assert_bad_parameters(dict(
            customer_guid=self.customer_guid,
            plan_guid=self.plan_guid,
            amount='0',
        ))
        assert_bad_parameters(dict(
            customer_guid=self.customer_guid,
            plan_guid=self.plan_guid,
            started_at='BAD_DATETIME',
        ))
        assert_bad_parameters(dict(
            customer_guid=self.plan_guid,
            plan_guid=self.plan_guid,
        ))
        assert_bad_parameters(dict(
            customer_guid=self.customer_guid,
            plan_guid=self.customer_guid,
        ))

    def test_create_subscription_with_started_at(self):
        customer_guid = self.customer_guid
        plan_guid = self.plan_guid
        amount = 5566
        now = datetime.datetime.utcnow()
        now_iso = now.isoformat()
        # next week
        next_transaction_at = datetime.datetime(2013, 8, 17)
        next_iso = next_transaction_at.isoformat()

        res = self.testapp.post(
            '/v1/subscriptions',
            dict(
                customer_guid=customer_guid,
                plan_guid=plan_guid,
                amount=amount,
                started_at='2013-08-17T00:00:00Z',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        self.failUnless('guid' in res.json)
        self.assertEqual(res.json['created_at'], now_iso)
        self.assertEqual(res.json['updated_at'], now_iso)
        self.assertEqual(res.json['next_transaction_at'], next_iso)
        self.assertEqual(res.json['period'], 0)
        self.assertEqual(res.json['amount'], amount)
        self.assertEqual(res.json['customer_guid'], customer_guid)
        self.assertEqual(res.json['plan_guid'], plan_guid)

    def test_create_subscription_with_started_at_and_timezone(self):
        customer_guid = self.customer_guid
        plan_guid = self.plan_guid
        amount = 5566
        # next week
        next_transaction_at = datetime.datetime(2013, 8, 17)
        next_iso = next_transaction_at.isoformat()

        res = self.testapp.post(
            '/v1/subscriptions',
            dict(
                customer_guid=customer_guid,
                plan_guid=plan_guid,
                amount=amount,
                started_at='2013-08-17T08:00:00+08:00',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        self.failUnless('guid' in res.json)
        self.assertEqual(res.json['next_transaction_at'], next_iso)
        self.assertEqual(res.json['period'], 0)

    def test_create_subscription_with_bad_api(self):
        self.testapp.post(
            '/v1/subscriptions',
            dict(
                customer_guid=self.customer_guid,
                plan_guid=self.plan_guid,
            ),
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'), 
            status=403,
        )

    def test_get_subscription(self):
        res = self.testapp.post(
            '/v1/subscriptions', 
            dict(
                customer_guid=self.customer_guid,
                plan_guid=self.plan_guid,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        created_subscriptions = res.json

        guid = created_subscriptions['guid']
        res = self.testapp.get(
            '/v1/subscriptions/{}'.format(guid), 
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        self.assertEqual(res.json, created_subscriptions)

    def test_get_non_existing_subscription(self):
        self.testapp.get(
            '/v1/subscriptions/NON_EXIST', 
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=404
        )

    def test_get_subscription_with_bad_api_key(self):
        res = self.testapp.post(
            '/v1/subscriptions', 
            dict(
                customer_guid=self.customer_guid,
                plan_guid=self.plan_guid,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )

        guid = res.json['guid']
        res = self.testapp.get(
            '/v1/subscriptions/{}'.format(guid), 
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'), 
            status=403,
        )

    def test_get_subscription_of_other_company(self):
        from billy.models.company import CompanyModel
        from billy.models.customer import CustomerModel
        from billy.models.plan import PlanModel

        company_model = CompanyModel(self.testapp.session)
        customer_model = CustomerModel(self.testapp.session)
        plan_model = PlanModel(self.testapp.session)
        with db_transaction.manager:
            other_company_guid = company_model.create(
                processor_key='MOCK_PROCESSOR_KEY',
            )
            other_customer_guid = customer_model.create(
                company_guid=other_company_guid
            )
            other_plan_guid = plan_model.create(
                company_guid=other_company_guid,
                frequency=plan_model.FREQ_WEEKLY,
                plan_type=plan_model.TYPE_CHARGE,
                amount=10,
            )
        other_company = company_model.get(other_company_guid)
        other_api_key = str(other_company.api_key)

        res = self.testapp.post(
            '/v1/subscriptions', 
            dict(
                customer_guid=other_customer_guid,
                plan_guid=other_plan_guid,
            ),
            extra_environ=dict(REMOTE_USER=other_api_key), 
            status=200,
        )
        other_guid = res.json['guid']

        self.testapp.get(
            '/v1/subscriptions/{}'.format(other_guid), 
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=403,
        )

    def test_create_subscription_to_other_company_customer(self):
        from billy.models.company import CompanyModel
        from billy.models.customer import CustomerModel

        company_model = CompanyModel(self.testapp.session)
        customer_model = CustomerModel(self.testapp.session)
        with db_transaction.manager:
            other_company_guid = company_model.create(
                processor_key='MOCK_PROCESSOR_KEY',
            )
            other_customer_guid = customer_model.create(
                company_guid=other_company_guid
            )

        self.testapp.post(
            '/v1/subscriptions', 
            dict(
                customer_guid=other_customer_guid,
                plan_guid=self.plan_guid,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=403,
        )

    def test_create_subscription_to_other_company_plan(self):
        from billy.models.company import CompanyModel
        from billy.models.plan import PlanModel

        company_model = CompanyModel(self.testapp.session)
        plan_model = PlanModel(self.testapp.session)
        with db_transaction.manager:
            other_company_guid = company_model.create(
                processor_key='MOCK_PROCESSOR_KEY',
            )
            other_plan_guid = plan_model.create(
                company_guid=other_company_guid,
                frequency=plan_model.FREQ_WEEKLY,
                plan_type=plan_model.TYPE_CHARGE,
                amount=10,
            )

        self.testapp.post(
            '/v1/subscriptions', 
            dict(
                customer_guid=self.customer_guid,
                plan_guid=other_plan_guid,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=403,
        )

    def test_cancel_subscription(self):
        from billy.models.subscription import SubscriptionModel
        from billy.models.transaction import TransactionModel

        subscription_model = SubscriptionModel(self.testapp.session)
        tx_model = TransactionModel(self.testapp.session)
        now = datetime.datetime.utcnow()

        with db_transaction.manager:
            subscription_guid = subscription_model.create(
                customer_guid=self.customer_guid,
                plan_guid=self.plan_guid,
            )
            tx_model.create(
                subscription_guid=subscription_guid,
                transaction_cls=tx_model.CLS_SUBSCRIPTION,
                transaction_type=tx_model.TYPE_CHARGE,
                amount=100, 
                scheduled_at=now,
            )

        with freeze_time('2013-08-16 07:00:00'):
            canceled_at = datetime.datetime.utcnow()
            res = self.testapp.post(
                '/v1/subscriptions/{}/cancel'.format(subscription_guid), 
                extra_environ=dict(REMOTE_USER=self.api_key), 
                status=200,
            )

        subscription = res.json
        self.assertEqual(subscription['canceled'], True)
        self.assertEqual(subscription['canceled_at'], canceled_at.isoformat())

    def test_cancel_a_canceled_subscription(self):
        from billy.models.subscription import SubscriptionModel
        from billy.models.transaction import TransactionModel

        subscription_model = SubscriptionModel(self.testapp.session)
        tx_model = TransactionModel(self.testapp.session)
        now = datetime.datetime.utcnow()

        with db_transaction.manager:
            subscription_guid = subscription_model.create(
                customer_guid=self.customer_guid,
                plan_guid=self.plan_guid,
            )
            tx_model.create(
                subscription_guid=subscription_guid,
                transaction_cls=tx_model.CLS_SUBSCRIPTION,
                transaction_type=tx_model.TYPE_CHARGE,
                amount=100, 
                scheduled_at=now,
            )

        self.testapp.post(
            '/v1/subscriptions/{}/cancel'.format(subscription_guid), 
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        self.testapp.post(
            '/v1/subscriptions/{}/cancel'.format(subscription_guid), 
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=400,
        )

    def test_cancel_subscription_to_other_company(self):
        from billy.models.subscription import SubscriptionModel
        from billy.models.company import CompanyModel 

        subscription_model = SubscriptionModel(self.testapp.session)
        company_model = CompanyModel(self.testapp.session)

        with db_transaction.manager:
            subscription_guid = subscription_model.create(
                customer_guid=self.customer_guid,
                plan_guid=self.plan_guid,
            )
            other_company_guid = company_model.create(
                processor_key='MOCK_PROCESSOR_KEY',
            )
            other_company = company_model.get(other_company_guid)
            other_api_key = str(other_company.api_key)

        self.testapp.post(
            '/v1/subscriptions/{}/cancel'.format(subscription_guid), 
            extra_environ=dict(REMOTE_USER=other_api_key), 
            status=403,
        )

    def test_cancel_subscription_with_prorated_refund(self):
        from billy.models.subscription import SubscriptionModel
        from billy.models.transaction import TransactionModel

        subscription_model = SubscriptionModel(self.testapp.session)
        tx_model = TransactionModel(self.testapp.session)
        now = datetime.datetime.utcnow()

        with db_transaction.manager:
            subscription_guid = subscription_model.create(
                customer_guid=self.customer_guid,
                plan_guid=self.plan_guid,
                amount=10000,
            )
            tx_guid = tx_model.create(
                subscription_guid=subscription_guid,
                transaction_cls=tx_model.CLS_SUBSCRIPTION,
                transaction_type=tx_model.TYPE_CHARGE,
                amount=10000, 
                scheduled_at=now,
            )
            subscription = subscription_model.get(subscription_guid)
            subscription.period = 1
            subscription.next_transaction_at = datetime.datetime(2013, 8, 23)
            self.testapp.session.add(subscription)

            transaction = tx_model.get(tx_guid)
            transaction.status = tx_model.STATUS_DONE
            transaction.external_id = 'MOCK_BALANCED_DEBIT_URI'
            self.testapp.session.add(transaction)

        refund_called = []

        def mock_refund(transaction):
            refund_called.append(transaction)
            return 'MOCK_PROCESSOR_REFUND_URI'

        mock_processor = flexmock(DummyProcessor)
        (
            mock_processor
            .should_receive('refund')
            .replace_with(mock_refund)
            .once()
        )

        with freeze_time('2013-08-17'):
            canceled_at = datetime.datetime.utcnow()
            res = self.testapp.post(
                '/v1/subscriptions/{}/cancel'.format(subscription_guid), 
                dict(prorated_refund=True),
                extra_environ=dict(REMOTE_USER=self.api_key), 
                status=200,
            )

        subscription = res.json
        self.assertEqual(subscription['canceled'], True)
        self.assertEqual(subscription['canceled_at'], canceled_at.isoformat())

        transaction = refund_called[0]
        self.testapp.session.add(transaction)
        self.assertEqual(transaction.refund_to.guid, tx_guid)
        self.assertEqual(transaction.subscription_guid, subscription_guid)
        # only one day is elapsed, and it is a weekly plan, so
        # it should be 10000 - (10000 / 7) and round to cent, 8571
        self.assertEqual(transaction.amount, 8571)
        self.assertEqual(transaction.status, tx_model.STATUS_DONE)

        res = self.testapp.get(
            '/v1/transactions', 
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        guids = [item['guid'] for item in res.json['items']]
        self.assertEqual(set(guids), set([tx_guid, transaction.guid]))

    def test_cancel_subscription_with_refund_amount(self):
        from billy.models.subscription import SubscriptionModel
        from billy.models.transaction import TransactionModel

        subscription_model = SubscriptionModel(self.testapp.session)
        tx_model = TransactionModel(self.testapp.session)
        now = datetime.datetime.utcnow()

        with db_transaction.manager:
            subscription_guid = subscription_model.create(
                customer_guid=self.customer_guid,
                plan_guid=self.plan_guid,
            )
            tx_guid = tx_model.create(
                subscription_guid=subscription_guid,
                transaction_cls=tx_model.CLS_SUBSCRIPTION,
                transaction_type=tx_model.TYPE_CHARGE,
                amount=1000, 
                scheduled_at=now,
            )
            subscription = subscription_model.get(subscription_guid)
            subscription.period = 1
            subscription.next_transaction_at = datetime.datetime(2013, 8, 23)
            self.testapp.session.add(subscription)

            transaction = tx_model.get(tx_guid)
            transaction.status = tx_model.STATUS_DONE
            transaction.external_id = 'MOCK_BALANCED_DEBIT_URI'
            self.testapp.session.add(transaction)

        refund_called = []

        def mock_refund(transaction):
            refund_called.append(transaction)
            return 'MOCK_PROCESSOR_REFUND_URI'

        mock_processor = flexmock(DummyProcessor)
        (
            mock_processor
            .should_receive('refund')
            .replace_with(mock_refund)
            .once()
        )

        res = self.testapp.post(
            '/v1/subscriptions/{}/cancel'.format(subscription_guid), 
            dict(refund_amount=234),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        subscription = res.json

        transaction = refund_called[0]
        self.testapp.session.add(transaction)
        self.assertEqual(transaction.refund_to.guid, tx_guid)
        self.assertEqual(transaction.subscription_guid, subscription_guid)
        self.assertEqual(transaction.amount, 234)
        self.assertEqual(transaction.status, tx_model.STATUS_DONE)

        res = self.testapp.get(
            '/v1/transactions', 
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        guids = [item['guid'] for item in res.json['items']]
        self.assertEqual(set(guids), set([tx_guid, transaction.guid]))

    def test_cancel_subscription_with_bad_arguments(self):
        from billy.models.subscription import SubscriptionModel
        from billy.models.transaction import TransactionModel

        subscription_model = SubscriptionModel(self.testapp.session)
        tx_model = TransactionModel(self.testapp.session)
        now = datetime.datetime.utcnow()

        with db_transaction.manager:
            subscription_guid = subscription_model.create(
                customer_guid=self.customer_guid,
                plan_guid=self.plan_guid,
                amount=10000,
            )
            tx_guid = tx_model.create(
                subscription_guid=subscription_guid,
                transaction_cls=tx_model.CLS_SUBSCRIPTION,
                transaction_type=tx_model.TYPE_CHARGE,
                amount=10000, 
                scheduled_at=now,
            )
            subscription = subscription_model.get(subscription_guid)
            subscription.period = 1
            subscription.next_transaction_at = datetime.datetime(2013, 8, 23)
            self.testapp.session.add(subscription)

            transaction = tx_model.get(tx_guid)
            transaction.status = tx_model.STATUS_DONE
            transaction.external_id = 'MOCK_BALANCED_DEBIT_URI'
            self.testapp.session.add(transaction)

        def assert_bad_parameters(kwargs):
            self.testapp.post(
                '/v1/subscriptions/{}/cancel'.format(subscription_guid), 
                kwargs,
                extra_environ=dict(REMOTE_USER=self.api_key), 
                status=400,
            )
        assert_bad_parameters(dict(prorated_refund=True, refund_amount=10))
        assert_bad_parameters(dict(refund_amount=10001))

    def test_transaction_list_by_subscription(self):
        from billy.models.transaction import TransactionModel
        from billy.models.subscription import SubscriptionModel
        subscription_model = SubscriptionModel(self.testapp.session)
        transaction_model = TransactionModel(self.testapp.session)
        with db_transaction.manager:
            subscription_guid1 = subscription_model.create(
                customer_guid=self.customer_guid,
                plan_guid=self.plan_guid,
            )
            subscription_guid2 = subscription_model.create(
                customer_guid=self.customer_guid,
                plan_guid=self.plan_guid,
            )
        guids1 = []
        guids2 = []
        with db_transaction.manager:
            for i in range(10):
                with freeze_time('2013-08-16 00:00:{:02}'.format(i + 1)):
                    guid = transaction_model.create(
                        subscription_guid=subscription_guid1,
                        transaction_cls=transaction_model.CLS_SUBSCRIPTION,
                        transaction_type=transaction_model.TYPE_CHARGE,
                        amount=10 * i,
                        payment_uri='/v1/cards/tester',
                        scheduled_at=datetime.datetime.utcnow(),
                    )
                    guids1.append(guid)
            for i in range(20):
                with freeze_time('2013-08-16 00:00:{:02}'.format(i + 1)):
                    guid = transaction_model.create(
                        subscription_guid=subscription_guid2,
                        transaction_cls=transaction_model.CLS_SUBSCRIPTION,
                        transaction_type=transaction_model.TYPE_CHARGE,
                        amount=10 * i,
                        payment_uri='/v1/cards/tester',
                        scheduled_at=datetime.datetime.utcnow(),
                    )
                    guids2.append(guid)
        guids1 = list(reversed(guids1))
        guids2 = list(reversed(guids2))

        res = self.testapp.get(
            '/v1/subscriptions/{}/transactions'.format(subscription_guid1),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        items = res.json['items']
        result_guids = [item['guid'] for item in items]
        self.assertEqual(result_guids, guids1)

        res = self.testapp.get(
            '/v1/subscriptions/{}/transactions'.format(subscription_guid2),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        items = res.json['items']
        result_guids = [item['guid'] for item in items]
        self.assertEqual(result_guids, guids2)

    def test_transaction_list_by_subscription_with_bad_api_key(self):
        from billy.models.subscription import SubscriptionModel
        subscription_model = SubscriptionModel(self.testapp.session)
        with db_transaction.manager:
            subscription_guid = subscription_model.create(
                customer_guid=self.customer_guid,
                plan_guid=self.plan_guid,
            )

        self.testapp.get(
            '/v1/subscriptions/{}/transactions'.format(subscription_guid),
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'), 
            status=403,
        )

    def test_subscription_list(self):
        from billy.models.subscription import SubscriptionModel
        subscription_model = SubscriptionModel(self.testapp.session)
        with db_transaction.manager:
            guids = []
            for i in range(4):
                with freeze_time('2013-08-16 00:00:{:02}'.format(i + 1)):
                    guid = subscription_model.create(
                        customer_guid=self.customer_guid,
                        plan_guid=self.plan_guid,
                    )
                    guids.append(guid)
        guids = list(reversed(guids))

        res = self.testapp.get(
            '/v1/subscriptions',
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        items = res.json['items']
        result_guids = [item['guid'] for item in items]
        self.assertEqual(result_guids, guids)

    def test_subscription_list_with_bad_api_key(self):
        self.testapp.get(
            '/v1/subscriptions',
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'), 
            status=403,
        )
