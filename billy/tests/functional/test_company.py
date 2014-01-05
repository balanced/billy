from __future__ import unicode_literals
import datetime

from freezegun import freeze_time

from billy.tests.functional.helper import ViewTestCase


@freeze_time('2013-08-16')
class TestCompanyViews(ViewTestCase):

    def test_create_company(self):
        processor_key = 'MOCK_PROCESSOR_KEY'
        now = datetime.datetime.utcnow()
        now_iso = now.isoformat()
        
        res = self.testapp.post(
            '/v1/companies', 
            dict(processor_key=processor_key), 
            status=200
        )
        self.failUnless('processor_key' not in res.json)
        self.failUnless('guid' in res.json)
        self.failUnless('api_key' in res.json)
        self.assertEqual(res.json['created_at'], now_iso)
        self.assertEqual(res.json['updated_at'], now_iso)

    def test_create_company_with_bad_parameters(self):
        self.testapp.post(
            '/v1/companies', 
            status=400,
        )

    def test_get_company(self):
        processor_key = 'MOCK_PROCESSOR_KEY'
        res = self.testapp.post(
            '/v1/companies', 
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
            '/v1/companies', 
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
            '/v1/companies', 
            dict(processor_key=processor_key), 
            status=200
        )
        api_key = str(res.json['api_key'])
        self.testapp.get(
            '/v1/companies/NON_EXIST', 
            extra_environ=dict(REMOTE_USER=api_key),
            status=404
        )

    def test_get_other_company(self):
        processor_key = 'MOCK_PROCESSOR_KEY'

        res = self.testapp.post(
            '/v1/companies', 
            dict(processor_key=processor_key), 
            status=200
        )
        api_key1 = str(res.json['api_key'])
        guid1 = res.json['guid']

        res = self.testapp.post(
            '/v1/companies', 
            dict(processor_key=processor_key), 
            status=200
        )
        api_key2 = str(res.json['api_key'])
        guid2 = res.json['guid']

        self.testapp.get(
            '/v1/companies/{}'.format(guid2), 
            extra_environ=dict(REMOTE_USER=api_key1), 
            status=403,
        )
        self.testapp.get(
            '/v1/companies/{}'.format(guid1), 
            extra_environ=dict(REMOTE_USER=api_key2), 
            status=403,
        )
