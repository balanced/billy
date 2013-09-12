from __future__ import unicode_literals
import datetime

import transaction
from freezegun import freeze_time

from billy.tests.unit.helper import ModelTestCase


@freeze_time('2013-08-16')
class TestCustomerModel(ModelTestCase):

    def setUp(self):
        from billy.models.company import CompanyModel
        super(TestCustomerModel, self).setUp()
        # build the basic scenario for plan model
        self.company_model = CompanyModel(self.session)
        with transaction.manager:
            self.company_guid = self.company_model.create('my_secret_key')

    def make_one(self, *args, **kwargs):
        from billy.models.customer import CustomerModel
        return CustomerModel(*args, **kwargs)

    def test_get_customer(self):
        model = self.make_one(self.session)

        customer = model.get('PL_NON_EXIST')
        self.assertEqual(customer, None)

        with self.assertRaises(KeyError):
            model.get('PL_NON_EXIST', raise_error=True)

        with transaction.manager:
            guid = model.create(company_guid=self.company_guid)

        customer = model.get(guid, raise_error=True)
        self.assertEqual(customer.guid, guid)

    def test_create(self):
        model = self.make_one(self.session)
        external_id = '5566_GOOD_BROTHERS'

        with transaction.manager:
            guid = model.create(
                company_guid=self.company_guid,
                external_id=external_id,
            )

        now = datetime.datetime.utcnow()

        customer = model.get(guid)
        self.assertEqual(customer.guid, guid)
        self.assert_(customer.guid.startswith('CU'))
        self.assertEqual(customer.company_guid, self.company_guid)
        self.assertEqual(customer.external_id, external_id)
        self.assertEqual(customer.deleted, False)
        self.assertEqual(customer.created_at, now)
        self.assertEqual(customer.updated_at, now)

    def test_create_different_created_updated_time(self):
        from billy.models import tables
        model = self.make_one(self.session)

        results = [
            datetime.datetime(2013, 8, 16, 1),
            datetime.datetime(2013, 8, 16, 2),
        ]

        def mock_utcnow():
            return results.pop(0)

        tables.set_now_func(mock_utcnow)

        with transaction.manager:
            guid = model.create(self.company_guid)

        customer = model.get(guid)
        self.assertEqual(customer.created_at, customer.updated_at)

    def test_update(self):
        model = self.make_one(self.session)

        with transaction.manager:
            guid = model.create(
                company_guid=self.company_guid,
                external_id='old id',
            )

        customer = model.get(guid)
        external_id = 'new external id'

        with transaction.manager:
            model.update(
                guid=guid,
                external_id=external_id,
            )

        customer = model.get(guid)
        self.assertEqual(customer.external_id, external_id)

    def test_update_updated_at(self):
        model = self.make_one(self.session)

        with transaction.manager:
            guid = model.create(company_guid=self.company_guid)

        customer = model.get(guid)
        created_at = customer.created_at

        # advanced the current date time
        with freeze_time('2013-08-16 07:00:01'):
            with transaction.manager:
                model.update(guid=guid)
            updated_at = datetime.datetime.utcnow()

        customer = model.get(guid)
        self.assertEqual(customer.updated_at, updated_at)
        self.assertEqual(customer.created_at, created_at)

        # advanced the current date time even more
        with freeze_time('2013-08-16 08:35:40'):
            # this should update the updated_at field only
            with transaction.manager:
                model.update(guid)
            updated_at = datetime.datetime.utcnow()

        customer = model.get(guid)
        self.assertEqual(customer.updated_at, updated_at)
        self.assertEqual(customer.created_at, created_at)

    def test_update_with_wrong_args(self):
        model = self.make_one(self.session)

        with transaction.manager:
            guid = model.create(company_guid=self.company_guid)

        # make sure passing wrong argument will raise error
        with self.assertRaises(TypeError):
            model.update(guid, wrong_arg=True, neme='john')

    def test_delete(self):
        model = self.make_one(self.session)

        with transaction.manager:
            guid = model.create(company_guid=self.company_guid)
            model.delete(guid)

        customer = model.get(guid)
        self.assertEqual(customer.deleted, True)

    def test_list_by_company_guid(self):
        model = self.make_one(self.session)

        # create another company with customers
        with transaction.manager:
            other_company_guid = self.company_model.create('my_secret_key')
            guids1 = []
            for i in range(2):
                with freeze_time('2013-08-16 00:00:{:02}'.format(i)):
                    guid = model.create(
                        company_guid=other_company_guid,
                    )
                    guids1.append(guid)
        with transaction.manager:
            guids2 = []
            for i in range(3):
                with freeze_time('2013-08-16 00:00:{:02}'.format(i)):
                    guid = model.create(
                        company_guid=self.company_guid,
                    )
                    guids2.append(guid)

        guids1 = list(reversed(guids1))
        guids2 = list(reversed(guids2))

        def assert_list_by_company_guid(
            company_guid, 
            expected, 
            offset=None, 
            limit=None,
        ):
            result = model.list_by_company_guid(
                company_guid, 
                offset=offset, 
                limit=limit,
            )
            result_guids = [s.guid for s in result]
            self.assertEqual(result_guids, expected)

        assert_list_by_company_guid(other_company_guid, guids1)
        assert_list_by_company_guid(other_company_guid, guids1[1:], offset=1)
        assert_list_by_company_guid(other_company_guid, guids1[2:], offset=2)
        assert_list_by_company_guid(other_company_guid, guids1[:1], limit=1)
        assert_list_by_company_guid(self.company_guid, guids2)
