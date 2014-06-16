from __future__ import unicode_literals

import transaction as db_transaction

from billy.tests.functional.helper import ViewTestCase


class TestAllowOrigin(ViewTestCase):

    def setUp(self):
        super(TestAllowOrigin, self).setUp()
        with db_transaction.manager:
            self.company = self.company_model.create(
                processor_key='MOCK_PROCESSOR_KEY',
            )
        self.api_key = str(self.company.api_key)

    def assert_allowed(self, origin):
        origin = str(origin)
        resp = self.testapp.options(
            '/v1/customers',
            headers={
                'Origin': origin,
            },
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=404,
        )
        self.assertEqual(
            resp.headers.get('Access-Control-Allow-Origin'),
            origin,
        )
        self.assertEqual(
            resp.headers.get('Access-Control-Allow-Credentials'),
            'true',
        )
        self.assertEqual(
            resp.headers.get('Access-Control-Allow-Methods'),
            'GET, POST, PUT, DELETE, PATCH, OPTIONS',
        )
        self.assertEqual(
            resp.headers.get('Access-Control-Allow-Headers'),
            'Content-Type,Authorization',
        )

    def assert_not_allowed(self, origin):
        origin = str(origin)
        resp = self.testapp.options(
            '/v1/customers',
            headers={
                'Origin': origin,
            },
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=404,
        )
        resp_allow_origin = resp.headers.get('Access-Control-Allow-Origin', [])
        self.assertNotIn(origin, resp_allow_origin)

    def test_allow_origin(self):
        self.testapp.app.registry.settings['api.allowed_origins'] = [
            'http://127.0.0.1',
            'http://localhost',
        ]
        self.assert_allowed('http://127.0.0.1')
        self.assert_allowed('http://127.0.0.1/')
        self.assert_allowed('http://127.0.0.1/foo')
        self.assert_allowed('http://127.0.0.1/foo/bar')
        self.assert_allowed('http://127.0.0.1:6060/foo/bar')
        self.assert_allowed('http://localhost/')
        self.assert_allowed('http://localhost:5050/')
        self.assert_allowed('http://localhost/foo')
        self.assert_allowed('http://localhost/foo/bar')

    def test_allow_origin_with_multiiple_line_cfg(self):
        self.testapp.app.registry.settings['api.allowed_origins'] = '\n'.join([
            'http://127.0.0.1',
            'http://localhost',
        ])
        self.assert_allowed('http://127.0.0.1')
        self.assert_allowed('http://localhost/')

    def test_not_allow_origin(self):
        self.testapp.app.registry.settings['api.allowed_origins'] = [
            'http://127.0.0.1',
            'http://localhost',
        ]
        self.assert_not_allowed('http://127.0.0.2')
        self.assert_not_allowed('http://127.0.0.2/')
        self.assert_not_allowed('http://127.0.0.2/foo')
        self.assert_not_allowed('http://127.0.0.2/foo/bar')
        self.assert_not_allowed('http://my-localhost/')
        self.assert_not_allowed('http://my-localhost/foo')
        self.assert_not_allowed('http://my-localhost/foo/bar')
