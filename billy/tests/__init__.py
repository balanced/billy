from __future__ import unicode_literals

import datetime
import unittest


from models import Company


class BaseTestCase(unittest.TestCase):
    def setUp(self):
        super(BaseTestCase, self).setUp()
        self.test_company_keys = ['BILLY_TEST_COMPANY_1',
                                  'BILLY_TEST_COMPANY_2',
                                  'BILLY_TEST_COMPANY_3']
        self.test_companies = []
        for api_key in self.test_company_keys:
            Company.query.filter(Company.processor_credential == api_key).delete()
            self.test_companies.append(
                Company.create('DUMMY', api_key, is_test=True))


def rel_delta_to_sec(rel):
    now = datetime.datetime.now()
    return ((now + rel) - now).total_seconds()
