import transaction as db_transaction

from billy.tests.functional.helper import ViewTestCase


class TestCustomerViews(ViewTestCase):

    def setUp(self):
        from billy.models.company import CompanyModel
        super(TestCustomerViews, self).setUp()
        model = CompanyModel(self.testapp.session)
        with db_transaction.manager:
            self.company_guid = model.create(processor_key='MOCK_PROCESSOR_KEY')

    def test_create_customer(self):
        res = self.testapp.post('/v1/customers/', status=200)
        self.failUnless('guid' in res.json)
        self.failUnless('created_at' in res.json)
        self.failUnless('updated_at' in res.json)

    def test_get_company(self):
        res = self.testapp.post('/v1/customers/', status=200)
        created_customer = res.json

        guid = created_customer['guid']
        res = self.testapp.get('/v1/customers/{}'.format(guid), status=200)
        self.assertEqual(res.json, created_customer)

    def test_get_non_existing_customer(self):
        self.testapp.get('/v1/customers/NON_EXIST', status=404)
