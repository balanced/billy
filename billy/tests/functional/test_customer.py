from __future__ import unicode_literals

import transaction as db_transaction

from billy.tests.functional.helper import ViewTestCase


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
        res = self.testapp.post(
            '/v1/customers/',
            dict(external_id='MOCK_EXTERNAL_ID'),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        self.failUnless('guid' in res.json)
        self.failUnless('created_at' in res.json)
        self.failUnless('updated_at' in res.json)
        self.assertEqual(res.json['external_id'], 'MOCK_EXTERNAL_ID')

    def test_create_customer_with_bad_api_key(self):
        self.testapp.post(
            '/v1/customers/',
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'), 
            status=403,
        )

    def test_get_customer(self):
        res = self.testapp.post(
            '/v1/customers/', 
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
            '/v1/customers/', 
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
