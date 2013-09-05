from __future__ import unicode_literals
import os
import unittest


class ViewTestCase(unittest.TestCase):
    
    def setUp(self):
        from webtest import TestApp
        from billy import main
        from billy.models import setup_database
        from billy.models.tables import DeclarativeBase

        if hasattr(self, 'settings'):
            settings = self.settings
        else:
            settings = {}

        # init database
        db_url = os.environ.get('BILLY_FUNC_TEST_DB', 'sqlite://')
        settings['sqlalchemy.url'] = db_url
        if hasattr(ViewTestCase, '_engine'):
            settings['engine'] = ViewTestCase._engine
        settings = setup_database({}, **settings)
        # we want to save and reuse the SQL connection if it is not SQLite,
        # otherwise, somehow, it will create too many connections to server
        # and make the testing results in failure
        if settings['engine'].name != 'sqlite':
            ViewTestCase._engine = settings['engine']
        DeclarativeBase.metadata.bind = settings['engine']
        DeclarativeBase.metadata.create_all()

        app = main({}, **settings)
        self.testapp = TestApp(app)
        self.testapp.session = settings['session']

    def tearDown(self):
        from billy.models.tables import DeclarativeBase
        self.testapp.session.remove()
        DeclarativeBase.metadata.drop_all()
