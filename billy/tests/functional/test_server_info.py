from __future__ import unicode_literals

from billy.tests.functional.helper import ViewTestCase


class TestServerInfo(ViewTestCase):

    def make_one(self):
        from billy.api.auth import get_remote_user
        return get_remote_user

    def test_server_info(self):
        res = self.testapp.get('/', status=200)
        self.assertIn('revision', res.json)
