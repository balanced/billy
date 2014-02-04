from __future__ import unicode_literals
import json

import mock
from freezegun import freeze_time

from billy.utils.generic import utc_now
from billy.tests.functional.helper import ViewTestCase


@freeze_time('2013-08-16')
class TestCompanyViews(ViewTestCase):

    def test_create_company(self):
        processor_key = 'MOCK_PROCESSOR_KEY'
        now = utc_now()
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

    def test_create_company_with_random_callback_keys(self):
        times = 100
        callback_keys = set()
        for _ in range(times):
            res = self.testapp.post(
                '/v1/companies',
                dict(processor_key='MOCK_PROCESSOR_KEY'),
                status=200
            )
            company = self.company_model.get(res.json['guid'])
            callback_keys.add(company.callback_key)
        # ensure callback keys won't repeat
        self.assertEqual(len(callback_keys), times)

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.callback')
    def test_callback(self, callback_method):
        res = self.testapp.post(
            '/v1/companies',
            dict(processor_key='MOCK_PROCESSOR_KEY'),
        )
        guid = res.json['guid']
        payload = dict(foo='bar')
        company = self.company_model.get(guid)
        res = self.testapp.post(
            '/v1/companies/{}/callbacks/{}'.format(guid, company.callback_key),
            json.dumps(payload),
            headers=[(b'content-type', b'application/json')],
        )
        self.assertEqual(res.json['code'], 'ok')
        callback_method.assert_called_once(company, payload)

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
        self.testapp.get(
            '/v1/companies/{}'.format(guid),
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'),
            status=403,
        )
        self.testapp.get(
            '/v1/companies/{}'.format(guid),
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
