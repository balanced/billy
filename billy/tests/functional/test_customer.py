from __future__ import unicode_literals
import datetime

import transaction as db_transaction
from freezegun import freeze_time

from billy.tests.functional.helper import ViewTestCase


@freeze_time('2013-08-16')
class TestCustomerViews(ViewTestCase):

    def setUp(self):
        from billy.models.company import CompanyModel
        super(TestCustomerViews, self).setUp()
        model = CompanyModel(self.testapp.session)
        with db_transaction.manager:
            self.company_guid = model.create(processor_key='MOCK_PROCESSOR_KEY')
        company = model.get(self.company_guid)
        self.api_key = str(company.api_key)

    def test_create_customer(self):
        now = datetime.datetime.utcnow()
        now_iso = now.isoformat()

        res = self.testapp.post(
            '/v1/customers',
            dict(external_id='MOCK_EXTERNAL_ID'),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        self.failUnless('guid' in res.json)
        self.assertEqual(res.json['created_at'], now_iso)
        self.assertEqual(res.json['updated_at'], now_iso)
        self.assertEqual(res.json['external_id'], 'MOCK_EXTERNAL_ID')
        self.assertEqual(res.json['company_guid'], self.company_guid)
        self.assertEqual(res.json['deleted'], False)

    def test_create_customer_with_bad_api_key(self):
        self.testapp.post(
            '/v1/customers',
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'), 
            status=403,
        )

    def test_get_customer(self):
        res = self.testapp.post(
            '/v1/customers', 
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        created_customer = res.json

        guid = created_customer['guid']
        res = self.testapp.get(
            '/v1/customers/{}'.format(guid), 
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        self.assertEqual(res.json, created_customer)

    def test_get_customer_with_bad_api_key(self):
        res = self.testapp.post(
            '/v1/customers', 
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        created_customer = res.json

        guid = created_customer['guid']
        res = self.testapp.get(
            '/v1/customers/{}'.format(guid), 
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'), 
            status=403,
        )

    def test_get_non_existing_customer(self):
        self.testapp.get(
            '/v1/customers/NON_EXIST', 
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=404
        )

    def test_get_customer_of_other_company(self):
        from billy.models.company import CompanyModel
        model = CompanyModel(self.testapp.session)
        with db_transaction.manager:
            other_company_guid = model.create(processor_key='MOCK_PROCESSOR_KEY')
        other_company = model.get(other_company_guid)
        other_api_key = str(other_company.api_key)
        res = self.testapp.post(
            '/v1/customers', 
            extra_environ=dict(REMOTE_USER=other_api_key), 
            status=200,
        )
        guid = res.json['guid']
        res = self.testapp.get(
            '/v1/customers/{}'.format(guid), 
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=403,
        )

    def test_customer_list(self):
        from billy.models.customer import CustomerModel 
        customer_model = CustomerModel(self.testapp.session)
        with db_transaction.manager:
            guids = []
            for i in range(4):
                with freeze_time('2013-08-16 00:00:{:02}'.format(i + 1)):
                    guid = customer_model.create(self.company_guid)
                    guids.append(guid)
        guids = list(reversed(guids))

        res = self.testapp.get(
            '/v1/customers',
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        items = res.json['items']
        result_guids = [item['guid'] for item in items]
        self.assertEqual(result_guids, guids)

    def test_customer_list_with_bad_api_key(self):
        self.testapp.get(
            '/v1/customers',
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'), 
            status=403,
        )

    def test_delete_customer(self):
        res = self.testapp.post(
            '/v1/customers',
            dict(external_id='MOCK_EXTERNAL_ID'),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        created_customer = res.json
        res = self.testapp.delete(
            '/v1/customers/{}'.format(created_customer['guid']),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        deleted_customer = res.json
        self.assertEqual(deleted_customer['deleted'], True)

    def test_delete_a_deleted_customer(self):
        res = self.testapp.post(
            '/v1/customers',
            dict(external_id='MOCK_EXTERNAL_ID'),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        created_customer = res.json
        self.testapp.delete(
            '/v1/customers/{}'.format(created_customer['guid']),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        self.testapp.delete(
            '/v1/customers/{}'.format(created_customer['guid']),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=400,
        )

    def test_delete_customer_with_bad_api_key(self):
        res = self.testapp.post(
            '/v1/customers',
            dict(external_id='MOCK_EXTERNAL_ID'),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        created_customer = res.json
        self.testapp.delete(
            '/v1/customers/{}'.format(created_customer['guid']),
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'), 
            status=403,
        )

    def test_delete_customer_of_other_company(self):
        from billy.models.company import CompanyModel
        model = CompanyModel(self.testapp.session)
        with db_transaction.manager:
            other_company_guid = model.create(processor_key='MOCK_PROCESSOR_KEY')
        other_company = model.get(other_company_guid)
        other_api_key = str(other_company.api_key)
        res = self.testapp.post(
            '/v1/customers', 
            extra_environ=dict(REMOTE_USER=other_api_key), 
            status=200,
        )
        guid = res.json['guid']
        self.testapp.delete(
            '/v1/customers/{}'.format(guid), 
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=403,
        )
