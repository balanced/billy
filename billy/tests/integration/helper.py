from __future__ import unicode_literals
import os
import base64
import unittest
import logging

import balanced
from wac import NoResultFound
from webtest import TestApp

logger = logging.getLogger(__name__)


class IntegrationTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.processor_key = os.environ.get('BILLY_TEST_PROCESSOR_KEY', None)
        cls.marketplace_uri = os.environ.get('BILLY_TEST_MARKETPLACE_URI', None)
        if cls.processor_key is None:
            api_key = balanced.APIKey().save()
            cls.processor_key = api_key.secret
            balanced.configure(cls.processor_key)
        try:
            cls.marketplace_uri = balanced.Marketplace.my_marketplace.href
        except (NoResultFound, balanced.exc.NoResultFound):
            cls.marketplace_uri = balanced.Marketplace().save().href
   
    def setUp(self):
        logger.info('Testing with Balanced API key %s', self.processor_key)
        logger.info('Testing with marketplace %s', self.marketplace_uri)
        self.target_url = os.environ.get(
            'BILLY_TEST_URL',
            'http://127.0.0.1:6543#requests')
        self.testapp = TestApp(self.target_url)

    def make_auth(self, api_key):
        """Make a basic authentication header and return

        """
        encoded = base64.b64encode(api_key + ':')
        return (b'authorization', b'basic {}'.format(encoded))
