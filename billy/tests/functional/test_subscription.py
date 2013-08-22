from __future__ import unicode_literals
import datetime

import transaction as db_transaction
from freezegun import freeze_time

from billy.tests.functional.helper import ViewTestCase


@freeze_time('2013-08-16')
class TestPlanViews(ViewTestCase):

    def setUp(self):
        from billy.models.company import CompanyModel
        from billy.models.customer import CustomerModel
        from billy.models.plan import PlanModel
        super(TestPlanViews, self).setUp()
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
                amount=10,
            )
        company = company_model.get(self.company_guid)
        self.api_key = str(company.api_key)

    def test_create_subscription(self):
        customer_guid = self.customer_guid
        plan_guid = self.plan_guid
        amount = '55.66'
        now = datetime.datetime.utcnow()
        now_iso = now.isoformat()

        res = self.testapp.post(
            '/v1/subscriptions/',
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
        self.assertEqual(res.json['next_transaction_at'], now_iso)
        self.assertEqual(res.json['period'], 0)
        self.assertEqual(res.json['amount'], amount)
        self.assertEqual(res.json['customer_guid'], customer_guid)
        self.assertEqual(res.json['plan_guid'], plan_guid)

    def test_create_subscription_with_bad_api(self):
        self.testapp.post(
            '/v1/subscriptions/',
            dict(
                customer_guid=self.customer_guid,
                plan_guid=self.plan_guid,
            ),
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'), 
            status=403,
        )

    def test_get_subscription(self):
        res = self.testapp.post(
            '/v1/subscriptions/', 
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
            '/v1/subscriptions/', 
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
            '/v1/subscriptions/', 
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

        other_company = company_model.get(other_company_guid)
        other_api_key = str(other_company.api_key)

        self.testapp.post(
            '/v1/subscriptions/', 
            dict(
                customer_guid=other_customer_guid,
                plan_guid=self.plan_guid,
            ),
            extra_environ=dict(REMOTE_USER=other_api_key), 
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
        other_company = company_model.get(other_company_guid)
        other_api_key = str(other_company.api_key)

        self.testapp.post(
            '/v1/subscriptions/', 
            dict(
                customer_guid=self.customer_guid,
                plan_guid=other_plan_guid,
            ),
            extra_environ=dict(REMOTE_USER=other_api_key), 
            status=403,
        )
