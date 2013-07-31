from base64 import b64encode

from unittest import TestCase

from api.app import app
from settings import TEST_API_KEY


class BaseTestCase(TestCase):

    def setUp(self):
        self.api_key = TEST_API_KEY
        self.auth_headers = {
            'Authorization': 'Basic {}'.format(b64encode(
                ':{}'.format(self.api_key)))
        }

        self.client = app.test_client()
        super(BaseTestCase, self).setUp()
