from __future__ import unicode_literals
import datetime

import transaction as db_transaction
from freezegun import freeze_time

from billy.tests.functional.helper import ViewTestCase


@freeze_time('2013-08-16')
class TestPlanViews(ViewTestCase):

    def setUp(self):
        from billy.models.company import CompanyModel
        super(TestPlanViews, self).setUp()
        model = CompanyModel(self.testapp.session)
        with db_transaction.manager:
            self.company_guid = model.create(processor_key='MOCK_PROCESSOR_KEY')
        company = model.get(self.company_guid)
        self.api_key = str(company.api_key)

    def test_create_plan(self):
        plan_type = 'charge'
        amount = '55.66'
        frequency = 'weekly'
        interval = 123
        now = datetime.datetime.utcnow()
        now_iso = now.isoformat()

        res = self.testapp.post(
            '/v1/plans/',
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
        self.assertEqual(res.json['company_guid'], self.company_guid)

    def test_create_plan_with_different_types(self):
        def assert_plan_type(plan_type):
            res = self.testapp.post(
                '/v1/plans/',
                dict(
                    plan_type=plan_type,
                    amount='55.66',
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
                '/v1/plans/',
                dict(
                    plan_type='charge',
                    amount='55.66',
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
            '/v1/plans/',
            dict(
                plan_type='charge',
                amount='55.66',
                frequency='weekly',
            ),
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'), 
            status=403,
        )

    def test_get_plan(self):
        res = self.testapp.post(
            '/v1/plans/', 
            dict(
                plan_type='charge',
                amount='55.66',
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
            '/v1/plans/', 
            dict(
                plan_type='charge',
                amount='55.66',
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
        from billy.models.company import CompanyModel
        model = CompanyModel(self.testapp.session)
        with db_transaction.manager:
            other_company_guid = model.create(processor_key='MOCK_PROCESSOR_KEY')
        other_company = model.get(other_company_guid)
        other_api_key = str(other_company.api_key)
        res = self.testapp.post(
            '/v1/plans/', 
            dict(
                plan_type='charge',
                amount='55.66',
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
