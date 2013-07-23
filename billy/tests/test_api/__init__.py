from base64 import b64encode

from unittest import TestCase

from api.app import app


class BaseTestCase(TestCase):

    def setUp(self):
        self.api_key = 'wyn6BvYH8AaKqkkq2xL0piuLvZoPymlD'
        self.auth_headers = {
            'Authorization': 'Basic {}'.format(b64encode(
                ':{}'.format(self.api_key)))
        }

        self.client = app.test_client()
        super(BaseTestCase, self).setUp()
