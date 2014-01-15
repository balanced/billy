from __future__ import unicode_literals

import os
import base64
import unittest


class IntegrationTestCase(unittest.TestCase):
   
    def setUp(self):
        from webtest import TestApp
        self.target_url = os.environ.get(
            'BILLY_TEST_URL',
            'http://127.0.0.1:6543#requests')
        self.processor_key = os.environ.get(
            'BILLY_TEST_PROCESSOR_KEY',
            'ef13dce2093b11e388de026ba7d31e6f')
        self.marketplace_uri = os.environ.get(
            'BILLY_TEST_MARKETPLACE_URI',
            '/v1/marketplaces/TEST-MP7hkE8rvpbtYu2dlO1jU2wg')
        self.testapp = TestApp(self.target_url)

    def make_auth(self, api_key):
        """Make a basic authentication header and return

        """
        encoded = base64.b64encode(api_key + ':')
        return (b'authorization', b'basic {}'.format(encoded))
