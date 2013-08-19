from __future__ import unicode_literals
import datetime

import transaction
from freezegun import freeze_time

from billy.tests.helper import ModelTestCase


@freeze_time('2013-08-16')
class TestCompanyModel(ModelTestCase):

    def make_one(self, *args, **kwargs):
        from billy.models.company import CompanyModel
        return CompanyModel(*args, **kwargs)

    def test_get(self):
        model = self.make_one(self.session)

        company = model.get('CP_NON_EXIST')
        self.assertEqual(company, None)

        with self.assertRaises(KeyError):
            model.get('CP_NON_EXIST', raise_error=True)

        with transaction.manager:
            guid = model.create(processor_key='my_secret_key')
            model.delete(guid)

        with self.assertRaises(KeyError):
            model.get(guid, raise_error=True)

        company = model.get(guid, ignore_deleted=False, raise_error=True)
        self.assertEqual(company.guid, guid)

    def test_create(self):
        model = self.make_one(self.session)
        name = 'awesome company'
        processor_key = 'my_secret_key'

        with transaction.manager:
            guid = model.create(
                name=name,
                processor_key=processor_key,
            )

        now = datetime.datetime.utcnow()

        company = model.get(guid)
        self.assertEqual(company.guid, guid)
        self.assert_(company.guid.startswith('CP'))
        self.assertEqual(company.name, name)
        self.assertEqual(company.processor_key, processor_key)
        self.assertNotEqual(company.api_key, None)
        self.assertEqual(company.deleted, False)
        self.assertEqual(company.created_at, now)
        self.assertEqual(company.updated_at, now)

    def test_update(self):
        model = self.make_one(self.session)

        with transaction.manager:
            guid = model.create(processor_key='my_secret_key')

        name = 'new name'
        processor_key = 'new processor key'
        api_key = 'new api key'

        with transaction.manager:
            model.update(
                guid=guid,
                name=name,
                api_key=api_key,
                processor_key=processor_key,
            )

        company = model.get(guid)
        self.assertEqual(company.name, name)
        self.assertEqual(company.processor_key, processor_key)
        self.assertEqual(company.api_key, api_key)

    def test_update_updated_at(self):
        model = self.make_one(self.session)

        with transaction.manager:
            guid = model.create(processor_key='my_secret_key')

        company = model.get(guid)
        created_at = company.created_at

        # advanced the current date time
        with freeze_time('2013-08-16 07:00:01'):
            with transaction.manager:
                model.update(guid=guid)
            updated_at = datetime.datetime.utcnow()

        company = model.get(guid)
        self.assertEqual(company.updated_at, updated_at)
        self.assertEqual(company.created_at, created_at)

        # advanced the current date time even more
        with freeze_time('2013-08-16 08:35:40'):
            with transaction.manager:
                model.update(guid)
            updated_at = datetime.datetime.utcnow()

        company = model.get(guid)
        self.assertEqual(company.updated_at, updated_at)
        self.assertEqual(company.created_at, created_at)

    def test_update_with_wrong_args(self):
        model = self.make_one(self.session)

        with transaction.manager:
            guid = model.create(processor_key='my_secret_key')

        # make sure passing wrong argument will raise error
        with self.assertRaises(TypeError):
            model.update(guid, wrong_arg=True, neme='john')

    def test_delete(self):
        model = self.make_one(self.session)

        with transaction.manager:
            guid = model.create(processor_key='my_secret_key')
            model.delete(guid)

        company = model.get(guid)
        self.assertEqual(company, None)

        company = model.get(guid, ignore_deleted=False)
        self.assertEqual(company.deleted, True)
