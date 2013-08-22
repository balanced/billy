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
        res = self.testapp.get('/v1/companies/{}'.format(guid), status=200)
        self.assertEqual(res.json, created_company)
