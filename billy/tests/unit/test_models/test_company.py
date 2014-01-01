from __future__ import unicode_literals
import datetime

import transaction
from freezegun import freeze_time

from billy.models import tables
from billy.tests.unit.helper import ModelTestCase


@freeze_time('2013-08-16')
class TestCompanyModel(ModelTestCase):

    def test_get(self):
        company = self.company_model.get('CP_NON_EXIST')
        self.assertEqual(company, None)

        with self.assertRaises(KeyError):
            self.company_model.get('CP_NON_EXIST', raise_error=True)

        with transaction.manager:
            guid = self.company_model.create(processor_key='my_secret_key')

        company = self.company_model.get(guid)
        self.assertEqual(company.guid, guid)

    def test_get_by_api_key(self):
        company = self.company_model.get_by_api_key('NON_EXIST_API')
        self.assertEqual(company, None)

        with self.assertRaises(KeyError):
            self.company_model.get_by_api_key('NON_EXIST_API', raise_error=True)

        with transaction.manager:
            guid = self.company_model.create(processor_key='my_secret_key')
            company = self.company_model.get(guid)
            api_key = company.api_key
            self.company_model.delete(guid)

        with self.assertRaises(KeyError):
            self.company_model.get_by_api_key(api_key, raise_error=True)

        company = self.company_model.get_by_api_key(
            api_key=api_key, 
            ignore_deleted=False, 
            raise_error=True,
        )
        self.assertEqual(company.guid, guid)

    def test_create(self):
        name = 'awesome company'
        processor_key = 'my_secret_key'

        with transaction.manager:
            guid = self.company_model.create(
                name=name,
                processor_key=processor_key,
            )

        now = datetime.datetime.utcnow()

        company = self.company_model.get(guid)
        self.assertEqual(company.guid, guid)
        self.assert_(company.guid.startswith('CP'))
        self.assertEqual(company.name, name)
        self.assertEqual(company.processor_key, processor_key)
        self.assertNotEqual(company.api_key, None)
        self.assertEqual(company.deleted, False)
        self.assertEqual(company.created_at, now)
        self.assertEqual(company.updated_at, now)

    def test_create_different_created_updated_time(self):
        results = [
            datetime.datetime(2013, 8, 16, 1),
            datetime.datetime(2013, 8, 16, 2),
        ]

        def mock_utcnow():
            return results.pop(0)

        tables.set_now_func(mock_utcnow)

        with transaction.manager:
            guid = self.company_model.create('my_secret_key')

        company = self.company_model.get(guid)
        self.assertEqual(company.created_at, company.updated_at)

    def test_update(self):
        with transaction.manager:
            guid = self.company_model.create(processor_key='my_secret_key')

        name = 'new name'
        processor_key = 'new processor key'
        api_key = 'new api key'

        with transaction.manager:
            self.company_model.update(
                guid=guid,
                name=name,
                api_key=api_key,
                processor_key=processor_key,
            )

        company = self.company_model.get(guid)
        self.assertEqual(company.name, name)
        self.assertEqual(company.processor_key, processor_key)
        self.assertEqual(company.api_key, api_key)

    def test_update_updated_at(self):
        with transaction.manager:
            guid = self.company_model.create(processor_key='my_secret_key')

        company = self.company_model.get(guid)
        created_at = company.created_at

        # advanced the current date time
        with freeze_time('2013-08-16 07:00:01'):
            with transaction.manager:
                self.company_model.update(guid=guid)
            updated_at = datetime.datetime.utcnow()

        company = self.company_model.get(guid)
        self.assertEqual(company.updated_at, updated_at)
        self.assertEqual(company.created_at, created_at)

        # advanced the current date time even more
        with freeze_time('2013-08-16 08:35:40'):
            with transaction.manager:
                self.company_model.update(guid)
            updated_at = datetime.datetime.utcnow()

        company = self.company_model.get(guid)
        self.assertEqual(company.updated_at, updated_at)
        self.assertEqual(company.created_at, created_at)

    def test_update_with_wrong_args(self):
        with transaction.manager:
            guid = self.company_model.create(processor_key='my_secret_key')

        # make sure passing wrong argument will raise error
        with self.assertRaises(TypeError):
            self.company_model.update(guid, wrong_arg=True, neme='john')

    def test_delete(self):
        with transaction.manager:
            guid = self.company_model.create(processor_key='my_secret_key')
            self.company_model.delete(guid)

        company = self.company_model.get(guid)
        self.assertEqual(company.deleted, True)
