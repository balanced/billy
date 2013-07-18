from __future__ import unicode_literals

from base64 import b64encode

from test import BaseTestCase


class AuthenticationTest(BaseTestCase):

    def setUp(self):
        self.bad_auth_headers = {
            'Authorization': "Basic {}".format(b64encode(':BADAPIKEY'))
        }
        super(AuthenticationTest, self).setUp()

    def test_no_key(self):
        resp = self.client.get('/v1/users/')
        self.assertEqual(resp.status_code, 401)

    def test_bad_auth_key(self):
        resp = self.client.get('/v1/users/',
                               headers=self.bad_auth_headers)
        self.assertEqual(resp.status_code, 401)

    def test_good_auth_key(self):
        resp = self.client.get('/v1/users/',
                               headers=self.auth_headers)
        self.assertEqual(resp.status_code, 200)

    def test_key_in_header(self):
        resp = self.client.get('/v1/users/',
                               headers={'Authorization': self.api_key})
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get('/v1/users/',
                               headers={'Authorization': 'BADKEY'})
        self.assertEqual(resp.status_code, 401)

    def test_key_in_get(self):
        resp = self.client.get('/v1/users/',
                               query_string={'api_key': self.api_key})
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get('/v1/users/',
                               query_string={'api_key': 'BADKEY'})
        self.assertEqual(resp.status_code, 401)
