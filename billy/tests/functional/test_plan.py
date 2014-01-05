from __future__ import unicode_literals
import datetime

import transaction as db_transaction
from freezegun import freeze_time

from billy.tests.functional.helper import ViewTestCase


@freeze_time('2013-08-16')
class TestPlanViews(ViewTestCase):

    def setUp(self):
        super(TestPlanViews, self).setUp()
        with db_transaction.manager:
            self.company = self.company_model.create(
                processor_key='MOCK_PROCESSOR_KEY',
            )
            self.company2 = self.company_model.create(
                processor_key='MOCK_PROCESSOR_KEY2',
            )
        self.api_key = str(self.company.api_key)

    def test_create_plan(self):
        plan_type = 'charge'
        amount = 5566
        frequency = 'weekly'
        interval = 123
        now = datetime.datetime.utcnow()
        now_iso = now.isoformat()

        res = self.testapp.post(
            '/v1/plans',
            dict(
                plan_type=plan_type,
                amount=amount,
                frequency=frequency,
                interval=interval,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        self.failUnless('guid' in res.json)
        self.assertEqual(res.json['created_at'], now_iso)
        self.assertEqual(res.json['updated_at'], now_iso)
        self.assertEqual(res.json['plan_type'], plan_type)
        self.assertEqual(res.json['amount'], amount)
        self.assertEqual(res.json['frequency'], frequency)
        self.assertEqual(res.json['interval'], interval)
        self.assertEqual(res.json['company_guid'], self.company.guid)
        self.assertEqual(res.json['deleted'], False)

    def test_create_plan_with_bad_parameters(self):
        def assert_bad_parameters(params):
            self.testapp.post(
                '/v1/plans',
                params,
                extra_environ=dict(REMOTE_USER=self.api_key), 
                status=400,
            )
        assert_bad_parameters(dict())
        assert_bad_parameters(dict(
            frequency='weekly',
            amount=5566,
        ))
        assert_bad_parameters(dict(
            plan_type='charge',
            amount=5566,
        ))
        assert_bad_parameters(dict(
            plan_type='charge',
            frequency='weekly',
        ))
        assert_bad_parameters(dict(
            plan_type='',
            frequency='weekly',
            amount=5566,
        ))
        assert_bad_parameters(dict(
            plan_type='super_charge',
            frequency='weekly',
            amount=5566,
        ))
        assert_bad_parameters(dict(
            plan_type='charge',
            frequency='',
            amount=5566,
        ))
        assert_bad_parameters(dict(
            plan_type='charge',
            frequency='decade',
            amount=5566,
        ))
        assert_bad_parameters(dict(
            plan_type='charge',
            frequency='weekly',
            amount='',
        ))
        assert_bad_parameters(dict(
            plan_type='charge',
            frequency='weekly',
            amount='-123',
        ))
        assert_bad_parameters(dict(
            plan_type='charge',
            frequency='weekly',
            amount=5566,
            interval='0',
        ))
        assert_bad_parameters(dict(
            plan_type='charge',
            frequency='weekly',
            amount=5566,
            interval='0.5',
        ))
        assert_bad_parameters(dict(
            plan_type='charge',
            frequency='weekly',
            amount=5566,
            interval='-123',
        ))
        assert_bad_parameters(dict(
            plan_type='charge',
            frequency='weekly',
            amount=49,
        ))

    def test_create_plan_with_empty_interval(self):
        # TODO: this case is a little bit strange, empty interval string
        # value should result in the default interval 1, however, WTForms
        # will yield None in this case, so we need to deal it specifically.
        # not sure is it a bug of WTForm, maybe we should workaround this later
        res = self.testapp.post(
            '/v1/plans',
            dict(
                plan_type='charge',
                amount=5566,
                frequency='weekly',
                interval='',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        self.assertEqual(res.json['interval'], 1)

    def test_create_plan_with_different_types(self):
        def assert_plan_type(plan_type):
            res = self.testapp.post(
                '/v1/plans',
                dict(
                    plan_type=plan_type,
                    amount=5566,
                    frequency='weekly',
                ),
                extra_environ=dict(REMOTE_USER=self.api_key), 
                status=200,
            )
            self.assertEqual(res.json['plan_type'], plan_type)

        assert_plan_type('charge')
        assert_plan_type('payout')

    def test_create_plan_with_different_frequency(self):
        def assert_frequency(frequency):
            res = self.testapp.post(
                '/v1/plans',
                dict(
                    plan_type='charge',
                    amount=5566,
                    frequency=frequency,
                ),
                extra_environ=dict(REMOTE_USER=self.api_key), 
                status=200,
            )
            self.assertEqual(res.json['frequency'], frequency)

        assert_frequency('daily')
        assert_frequency('weekly')
        assert_frequency('monthly')
        assert_frequency('yearly')

    def test_create_plan_with_bad_api_key(self):
        self.testapp.post(
            '/v1/plans',
            dict(
                plan_type='charge',
                amount=5566,
                frequency='weekly',
            ),
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'), 
            status=403,
        )

    def test_get_plan(self):
        res = self.testapp.post(
            '/v1/plans', 
            dict(
                plan_type='charge',
                amount=5566,
                frequency='weekly',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        created_plan = res.json

        guid = created_plan['guid']
        res = self.testapp.get(
            '/v1/plans/{}'.format(guid), 
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        self.assertEqual(res.json, created_plan)

    def test_get_non_existing_plan(self):
        self.testapp.get(
            '/v1/plans/NON_EXIST', 
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=404
        )

    def test_get_plan_with_bad_api_key(self):
        res = self.testapp.post(
            '/v1/plans', 
            dict(
                plan_type='charge',
                amount=5566,
                frequency='weekly',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )

        guid = res.json['guid']
        res = self.testapp.get(
            '/v1/plans/{}'.format(guid), 
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'), 
            status=403,
        )

    def test_get_plan_of_other_company(self):
        with db_transaction.manager:
            other_company = self.company_model.create(
                processor_key='MOCK_PROCESSOR_KEY',
            )
        other_api_key = str(other_company.api_key)
        res = self.testapp.post(
            '/v1/plans', 
            dict(
                plan_type='charge',
                amount=5566,
                frequency='weekly',
            ),
            extra_environ=dict(REMOTE_USER=other_api_key), 
            status=200,
        )
        guid = res.json['guid']
        res = self.testapp.get(
            '/v1/plans/{}'.format(guid), 
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=403,
        )

    def test_plan_list(self):
        with db_transaction.manager:
            # make some plans in other company, make sure they will not be 
            # listed
            for i in range(4):
                with freeze_time('2013-08-16 00:00:{:02}'.format(i + 1)):
                    self.plan_model.create(
                        company=self.company2,
                        plan_type=self.plan_model.TYPE_CHARGE,
                        amount=7788,
                        frequency=self.plan_model.FREQ_DAILY,
                    )

            guids = []
            for i in range(4):
                with freeze_time('2013-08-16 00:00:{:02}'.format(i + 1)):
                    plan = self.plan_model.create(
                        company=self.company,
                        plan_type=self.plan_model.TYPE_CHARGE,
                        amount=5566,
                        frequency=self.plan_model.FREQ_DAILY,
                    )
                    guids.append(plan.guid)
        guids = list(reversed(guids))

        res = self.testapp.get(
            '/v1/plans',
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        items = res.json['items']
        result_guids = [item['guid'] for item in items]
        self.assertEqual(result_guids, guids)

    def test_plan_customer_and_subscription_list(self):
        # make some records in other comapny to make sure they will not be 
        # included
        with db_transaction.manager:
            other_plan = self.plan_model.create(
                company=self.company2,
                plan_type=self.plan_model.TYPE_CHARGE,
                amount=5566,
                frequency=self.plan_model.FREQ_DAILY,
            )
        with db_transaction.manager:
            for i in range(4):
                with freeze_time('2013-08-16 00:00:{:02}'.format(i + 1)):
                    other_customer = self.customer_model.create(self.company2)
                    subscription = self.subscription_model.create(
                        plan=other_plan,
                        customer=other_customer,
                    )

        with db_transaction.manager:
            plan = self.plan_model.create(
                company=self.company,
                plan_type=self.plan_model.TYPE_CHARGE,
                amount=5566,
                frequency=self.plan_model.FREQ_DAILY,
            )
        with db_transaction.manager:
            customer_guids = []
            subscription_guids = []
            for i in range(4):
                with freeze_time('2013-08-16 00:00:{:02}'.format(i + 1)):
                    customer = self.customer_model.create(company=self.company)
                    subscription = self.subscription_model.create(
                        plan=plan,
                        customer=customer,
                    )
                    customer_guids.append(customer.guid)
                    subscription_guids.append(subscription.guid)
        customer_guids = list(reversed(customer_guids))
        subscription_guids = list(reversed(subscription_guids))

        res = self.testapp.get(
            '/v1/plans/{}/customers'.format(plan.guid),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        items = res.json['items']
        result_guids = [item['guid'] for item in items]
        self.assertEqual(result_guids, customer_guids)

        res = self.testapp.get(
            '/v1/plans/{}/subscriptions'.format(plan.guid),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        items = res.json['items']
        result_guids = [item['guid'] for item in items]
        self.assertEqual(result_guids, subscription_guids)

    def test_plan_transaction_list(self):
        # create some transactions in other to make sure they will not be included
        # in the result
        with db_transaction.manager:
            other_customer = self.customer_model.create(self.company2)
            other_plan = self.plan_model.create(
                company=self.company2,
                plan_type=self.plan_model.TYPE_CHARGE,
                amount=7788,
                frequency=self.plan_model.FREQ_DAILY,
            )
            other_subscription = self.subscription_model.create(
                customer=other_customer,
                plan=other_plan,
            )
            other_invoice = self.invoice_model.create(
                customer=other_customer,
                amount=9999,
            )
            for i in range(4):
                self.transaction_model.create(
                    invoice=other_invoice,
                    transaction_cls=self.transaction_model.CLS_INVOICE,
                    transaction_type=self.transaction_model.TYPE_CHARGE,
                    amount=100,
                    funding_instrument_uri='/v1/cards/tester',
                    scheduled_at=datetime.datetime.utcnow(),
                )
            for i in range(4):
                self.transaction_model.create(
                    subscription=other_subscription,
                    transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                    transaction_type=self.transaction_model.TYPE_CHARGE,
                    amount=100,
                    funding_instrument_uri='/v1/cards/tester',
                    scheduled_at=datetime.datetime.utcnow(),
                )

        with db_transaction.manager:
            customer = self.customer_model.create(self.company)
            plan = self.plan_model.create(
                company=self.company,
                plan_type=self.plan_model.TYPE_CHARGE,
                amount=5566,
                frequency=self.plan_model.FREQ_DAILY,
            )
            plan2 = self.plan_model.create(
                company=self.company,
                plan_type=self.plan_model.TYPE_CHARGE,
                amount=5566,
                frequency=self.plan_model.FREQ_DAILY,
            )
            subscription = self.subscription_model.create(
                customer=customer,
                plan=plan,
            )
            subscription2 = self.subscription_model.create(
                customer=customer,
                plan=plan2,
            )
            invoice = self.invoice_model.create(
                customer=customer,
                amount=7788,
            )
            # make sure invoice transaction will not be included
            self.transaction_model.create(
                invoice=invoice,
                transaction_cls=self.transaction_model.CLS_INVOICE,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=100,
                funding_instrument_uri='/v1/cards/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )
            # make sure transaction of other plan will not be included
            self.transaction_model.create(
                subscription=subscription2,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=100,
                funding_instrument_uri='/v1/cards/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )
            
            guids = []
            for i in range(4):
                with freeze_time('2013-08-16 02:00:{:02}'.format(i + 1)):
                    transaction = self.transaction_model.create(
                        subscription=subscription,
                        transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                        transaction_type=self.transaction_model.TYPE_CHARGE,
                        amount=100,
                        funding_instrument_uri='/v1/cards/tester',
                        scheduled_at=datetime.datetime.utcnow(),
                    )
                    guids.append(transaction.guid)
        guids = list(reversed(guids))

        res = self.testapp.get(
            '/v1/plans/{}/transactions'.format(plan.guid),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        items = res.json['items']
        result_guids = [item['guid'] for item in items]
        self.assertEqual(result_guids, guids)

    def test_plan_list_with_bad_api_key(self):
        with db_transaction.manager:
            plan = self.plan_model.create(
                company=self.company,
                plan_type=self.plan_model.TYPE_CHARGE,
                amount=5566,
                frequency=self.plan_model.FREQ_DAILY,
            )
        self.testapp.get(
            '/v1/plans',
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'), 
            status=403,
        )
        for list_name in [
            'customers',
            'subscriptions',
            'transactions',
        ]:
            self.testapp.get(
                '/v1/plans/{}/{}'.format(plan.guid, list_name),
                extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'), 
                status=403,
            )

    def test_delete_plan(self):
        res = self.testapp.post(
            '/v1/plans', 
            dict(
                plan_type='charge',
                amount=5566,
                frequency='weekly',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        created_plan = res.json
        res = self.testapp.delete(
            '/v1/plans/{}'.format(created_plan['guid']), 
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        deleted_plan = res.json
        self.assertEqual(deleted_plan['deleted'], True)

    def test_delete_a_deleted_plan(self):
        res = self.testapp.post(
            '/v1/plans', 
            dict(
                plan_type='charge',
                amount=5566,
                frequency='weekly',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        created_plan = res.json
        self.testapp.delete(
            '/v1/plans/{}'.format(created_plan['guid']), 
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        # TODO: should we use conflict or other code rather than
        # 400 here?
        self.testapp.delete(
            '/v1/plans/{}'.format(created_plan['guid']), 
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=400,
        )

    def test_delete_plan_with_bad_api_key(self):
        res = self.testapp.post(
            '/v1/plans', 
            dict(
                plan_type='charge',
                amount=5566,
                frequency='weekly',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        created_plan = res.json
        self.testapp.delete(
            '/v1/plans/{}'.format(created_plan['guid']), 
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'), 
            status=403,
        )

    def test_delete_plan_of_other_company(self):
        with db_transaction.manager:
            other_company = self.company_model.create(
                processor_key='MOCK_PROCESSOR_KEY',
            )
        other_api_key = str(other_company.api_key)
        res = self.testapp.post(
            '/v1/plans', 
            dict(
                plan_type='charge',
                amount=5566,
                frequency='weekly',
            ),
            extra_environ=dict(REMOTE_USER=other_api_key), 
            status=200,
        )
        guid = res.json['guid']
        self.testapp.delete(
            '/v1/plans/{}'.format(guid), 
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=403,
        )
