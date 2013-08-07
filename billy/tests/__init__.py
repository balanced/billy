from __future__ import unicode_literals

import datetime
import unittest


from models import ProcessorType, Company


class BaseTestCase(unittest.TestCase):
    def setUp(self):
        super(BaseTestCase, self).setUp()
        self.test_company_keys = ['BILLY_TEST_KEY_1',
                                  'BILLY_TEST_KEY_2',
                                  'BILLY_TEST_KEY_3']
        self.test_companies = []
        for credential in self.test_company_keys:
            Company.query.filter(Company.processor_credential == credential).delete()
            self.test_companies.append(
                Company.create(ProcessorType.DUMMY, credential, is_test=True))


def rel_delta_to_sec(rel):
    now = datetime.datetime.now()
    return ((now + rel) - now).total_seconds()
