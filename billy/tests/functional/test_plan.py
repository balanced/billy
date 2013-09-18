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
        self.assertEqual(res.json['company_guid'], self.company_guid)
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
            amount='55.66',
        ))
        assert_bad_parameters(dict(
            plan_type='charge',
            amount='55.66',
        ))
        assert_bad_parameters(dict(
            plan_type='charge',
            frequency='weekly',
        ))
        assert_bad_parameters(dict(
            plan_type='',
            frequency='weekly',
            amount='55.66',
        ))
        assert_bad_parameters(dict(
            plan_type='super_charge',
            frequency='weekly',
            amount='55.66',
        ))
        assert_bad_parameters(dict(
            plan_type='charge',
            frequency='',
            amount='55.66',
        ))
        assert_bad_parameters(dict(
            plan_type='charge',
            frequency='decade',
            amount='55.66',
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
            amount='55.66',
            interval='0',
        ))
        assert_bad_parameters(dict(
            plan_type='charge',
            frequency='weekly',
            amount='55.66',
            interval='0.5',
        ))
        assert_bad_parameters(dict(
            plan_type='charge',
            frequency='weekly',
            amount='55.66',
            interval='-123',
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
                amount='55.66',
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
                '/v1/plans',
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
            '/v1/plans',
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
            '/v1/plans', 
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
            '/v1/plans', 
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
            '/v1/plans', 
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

    def test_plan_list(self):
        from billy.models.plan import PlanModel 
        plan_model = PlanModel(self.testapp.session)
        with db_transaction.manager:
            guids = []
            for i in range(4):
                with freeze_time('2013-08-16 00:00:{:02}'.format(i + 1)):
                    guid = plan_model.create(
                        company_guid=self.company_guid,
                        plan_type=plan_model.TYPE_CHARGE,
                        amount=55.66,
                        frequency=plan_model.FREQ_DAILY,
                    )
                    guids.append(guid)
        guids = list(reversed(guids))

        res = self.testapp.get(
            '/v1/plans',
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        items = res.json['items']
        result_guids = [item['guid'] for item in items]
        self.assertEqual(result_guids, guids)

    def test_plan_list_with_bad_api_key(self):
        self.testapp.get(
            '/v1/plans',
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'), 
            status=403,
        )

    def test_delete_plan(self):
        res = self.testapp.post(
            '/v1/plans', 
            dict(
                plan_type='charge',
                amount='55.66',
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
                amount='55.66',
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
                amount='55.66',
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
        from billy.models.company import CompanyModel
        model = CompanyModel(self.testapp.session)
        with db_transaction.manager:
            other_company_guid = model.create(processor_key='MOCK_PROCESSOR_KEY')
        other_company = model.get(other_company_guid)
        other_api_key = str(other_company.api_key)
        res = self.testapp.post(
            '/v1/plans', 
            dict(
                plan_type='charge',
                amount='55.66',
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
