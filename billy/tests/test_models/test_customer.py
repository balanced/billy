from __future__ import unicode_literals
import datetime

import transaction
from freezegun import freeze_time

from billy.tests.helper import ModelTestCase


@freeze_time('2013-08-16')
class TestCustomerModel(ModelTestCase):

    def setUp(self):
        from billy.models.company import CompanyModel
        super(TestCustomerModel, self).setUp()
        # build the basic scenario for plan model
        self.company_model = CompanyModel(self.session)
        with transaction.manager:
            self.company_guid = self.company_model.create_company('my_secret_key')

    def make_one(self, *args, **kwargs):
        from billy.models.customer import CustomerModel
        return CustomerModel(*args, **kwargs)

    def test_get_customer(self):
        model = self.make_one(self.session)

        customer = model.get_customer_by_guid('PL_NON_EXIST')
        self.assertEqual(customer, None)

        with self.assertRaises(KeyError):
            model.get_customer_by_guid('PL_NON_EXIST', raise_error=True)

        with transaction.manager:
            guid = model.create_customer(
                company_guid=self.company_guid, 
                payment_uri='/v1/credit_card/id',
            )
            model.delete_customer(guid)

        with self.assertRaises(KeyError):
            model.get_customer_by_guid(guid, raise_error=True)

        customer = model.get_customer_by_guid(guid, ignore_deleted=False, raise_error=True)
        self.assertEqual(customer.guid, guid)

    def test_create_customer(self):
        model = self.make_one(self.session)
        name = 'Tom'
        payment_uri = '/v1/credit_card/id'
        external_id = '5566_GOOD_BROTHERS'

        with transaction.manager:
            guid = model.create_customer(
                company_guid=self.company_guid,
                payment_uri=payment_uri,
                name=name,
                external_id=external_id,
            )

        now = datetime.datetime.utcnow()

        customer = model.get_customer_by_guid(guid)
        self.assertEqual(customer.guid, guid)
        self.assert_(customer.guid.startswith('CU'))
        self.assertEqual(customer.company_guid, self.company_guid)
        self.assertEqual(customer.name, name)
        self.assertEqual(customer.payment_uri, payment_uri)
        self.assertEqual(customer.external_id, external_id)
        self.assertEqual(customer.deleted, False)
        self.assertEqual(customer.created_at, now)
        self.assertEqual(customer.updated_at, now)

    def test_update_customer(self):
        model = self.make_one(self.session)

        with transaction.manager:
            guid = model.create_customer(
                company_guid=self.company_guid,
                payment_uri='/v1/credit_card/id',
                external_id='old id',
                name='old name',
            )

        customer = model.get_customer_by_guid(guid)
        name = 'new name'
        payment_uri = 'new payment uri'
        external_id = 'new external id'

        with transaction.manager:
            model.update_customer(
                guid=guid,
                payment_uri=payment_uri,
                name=name,
                external_id=external_id,
            )

        customer = model.get_customer_by_guid(guid)
        self.assertEqual(customer.name, name)
        self.assertEqual(customer.payment_uri, payment_uri)
        self.assertEqual(customer.external_id, external_id)

    def test_update_customer_updated_at(self):
        model = self.make_one(self.session)

        with transaction.manager:
            guid = model.create_customer(
                company_guid=self.company_guid,
                payment_uri='/v1/credit_card/id',
            )

        customer = model.get_customer_by_guid(guid)
        created_at = customer.created_at

        # advanced the current date time
        with freeze_time('2013-08-16 07:00:01'):
            with transaction.manager:
                model.update_customer(guid=guid)
            updated_at = datetime.datetime.utcnow()

        customer = model.get_customer_by_guid(guid)
        self.assertEqual(customer.updated_at, updated_at)
        self.assertEqual(customer.created_at, created_at)

        # advanced the current date time even more
        with freeze_time('2013-08-16 08:35:40'):
            # this should update the updated_at field only
            with transaction.manager:
                model.update_customer(guid)
            updated_at = datetime.datetime.utcnow()

        customer = model.get_customer_by_guid(guid)
        self.assertEqual(customer.updated_at, updated_at)
        self.assertEqual(customer.created_at, created_at)

        # make sure passing wrong argument will raise error
        with self.assertRaises(TypeError):
            model.update_customer(guid, wrong_arg=True, neme='john')

    def test_delete_customer(self):
        model = self.make_one(self.session)

        with transaction.manager:
            guid = model.create_customer(
                company_guid=self.company_guid,
                payment_uri='/v1/credit_card/id',
            )
            model.delete_customer(guid)

        customer = model.get_customer_by_guid(guid)
        self.assertEqual(customer, None)

        customer = model.get_customer_by_guid(guid, ignore_deleted=False)
        self.assertEqual(customer.deleted, True)
