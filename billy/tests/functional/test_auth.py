from __future__ import unicode_literals

from webtest.app import TestRequest

from billy.tests.functional.helper import ViewTestCase


class TestAuth(ViewTestCase):

    def make_one(self):
        from billy.api.auth import get_remote_user
        return get_remote_user

    def test_get_remote(self):
        get_remote_user = self.make_one()

        encoded = 'USERNAME:PASSWORD'.encode('base64')
        auth = 'basic {}'.format(encoded)

        request = TestRequest(dict(HTTP_AUTHORIZATION=auth))
        user = get_remote_user(request)
        self.assertEqual(user, 'USERNAME')

    def test_get_remote_without_base64_part(self):
        get_remote_user = self.make_one()

        encoded = 'USERNAME'.encode('base64')
        auth = 'basic {}'.format(encoded)

        request = TestRequest(dict(HTTP_AUTHORIZATION=auth))
        user = get_remote_user(request)
        self.assertEqual(user, None)

    def test_get_remote_bad_base64(self):
        get_remote_user = self.make_one()
        request = TestRequest(dict(HTTP_AUTHORIZATION='basic Breaking####Bad'))
        user = get_remote_user(request)
        self.assertEqual(user, None)

    def test_get_remote_without_colon(self):
        get_remote_user = self.make_one()
        request = TestRequest(dict(HTTP_AUTHORIZATION='basic'))
        user = get_remote_user(request)
        self.assertEqual(user, None)

    def test_get_remote_non_basic(self):
        get_remote_user = self.make_one()
        request = TestRequest(dict(HTTP_AUTHORIZATION='foobar XXX'))
        user = get_remote_user(request)
        self.assertEqual(user, None)

    def test_get_remote_user_with_empty_environ(self):
        get_remote_user = self.make_one()
        request = TestRequest({})
        user = get_remote_user(request)
        self.assertEqual(user, None)

    def test_basic_auth_tween(self):
        from billy.api.auth import basic_auth_tween_factory

        encoded = 'USERNAME:PASSWORD'.encode('base64')
        auth = 'basic {}'.format(encoded)
        request = TestRequest(dict(HTTP_AUTHORIZATION=auth))

        called = []

        def handler(request):
            called.append(True)
            return 'RESPONSE'

        basic_auth_tween = basic_auth_tween_factory(handler, None)
        response = basic_auth_tween(request)

        self.assertEqual(response, 'RESPONSE')
        self.assertEqual(called, [True])
