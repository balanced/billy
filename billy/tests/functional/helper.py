import unittest


class ViewTestCase(unittest.TestCase):
    
    def setUp(self):
        from webtest import TestApp
        from billy import main
        from billy.models import setup_database
        from billy.models.tables import DeclarativeBase

        # init database
        settings = {
            'sqlalchemy.url': 'sqlite:///'
        }
        settings = setup_database({}, **settings)
        DeclarativeBase.metadata.create_all(bind=settings['session'].get_bind())

        app = main({}, **settings)
        self.testapp = TestApp(app)
        self.testapp.session = settings['session']

    def tearDown(self):
        self.testapp.session.remove()
