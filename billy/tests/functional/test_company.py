from __future__ import unicode_literals

from billy.tests.functional.helper import ViewTestCase


class TestCompanyViews(ViewTestCase):

    def test_create_company(self):
        processor_key = 'MOCK_PROCESSOR_KEY'
        res = self.testapp.post(
            '/v1/companies/', 
            dict(processor_key=processor_key), 
            status=200
        )
        self.failUnless('processor_key' not in res.json)
        self.failUnless('guid' in res.json)
        self.failUnless('api_key' in res.json)
        self.failUnless('created_at' in res.json)
        self.failUnless('updated_at' in res.json)

    def test_get_company(self):
        processor_key = 'MOCK_PROCESSOR_KEY'
        res = self.testapp.post(
            '/v1/companies/', 
            dict(processor_key=processor_key), 
            status=200
        )
        created_company = res.json
        guid = created_company['guid']
        api_key = str(created_company['api_key'])
        res = self.testapp.get(
            '/v1/companies/{}'.format(guid), 
            extra_environ=dict(REMOTE_USER=api_key), 
            status=200,
        )
        self.assertEqual(res.json, created_company)

    def test_get_company_with_bad_api_key(self):
        processor_key = 'MOCK_PROCESSOR_KEY'
        res = self.testapp.post(
            '/v1/companies/', 
            dict(processor_key=processor_key), 
            status=200
        )
        created_company = res.json
        guid = created_company['guid']
        res = self.testapp.get(
            '/v1/companies/{}'.format(guid), 
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'), 
            status=403,
        )

    def test_get_non_existing_company(self):
        processor_key = 'MOCK_PROCESSOR_KEY'
        res = self.testapp.post(
            '/v1/companies/', 
            dict(processor_key=processor_key), 
            status=200
        )
        api_key = str(res.json['api_key'])
        self.testapp.get(
            '/v1/companies/NON_EXIST', 
            extra_environ=dict(REMOTE_USER=api_key),
            status=404
        )
