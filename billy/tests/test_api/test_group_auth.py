from __future__ import unicode_literals

from base64 import b64encode

from . import BaseTestCase


class GroupAuthenticationTest(BaseTestCase):

    def setUp(self):
        self.bad_auth_headers = {
            'Authorization': "Basic {}".format(b64encode(':BADAPIKEY'))
        }
        super(GroupAuthenticationTest, self).setUp()

    def test_no_key(self):
        resp = self.client.get('/auth/')
        self.assertEqual(resp.status_code, 401)

    def test_bad_auth_key(self):
        resp = self.client.get('/auth/',
                               headers=self.bad_auth_headers)
        self.assertEqual(resp.status_code, 401)

    def test_good_auth_key(self):
        resp = self.client.get('/auth/',
                               headers=self.auth_headers)
        self.assertEqual(resp.status_code, 200)

    def test_key_in_header(self):
        resp = self.client.get('/auth/',
                               headers={'Authorization': self.api_key})
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get('/auth/',
                               headers={'Authorization': 'BADKEY'})
        self.assertEqual(resp.status_code, 401)

    def test_key_in_get(self):
        resp = self.client.get('/auth/',
                               query_string={'api_key': self.api_key})
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get('/auth/',
                               query_string={'api_key': 'BADKEY'})
        self.assertEqual(resp.status_code, 401)
