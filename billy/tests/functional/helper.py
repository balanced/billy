from __future__ import unicode_literals
import os
import unittest

from webtest import TestApp
from pyramid.testing import DummyRequest

from billy import main
from billy.models import setup_database
from billy.models.tables import DeclarativeBase
from billy.models.model_factory import ModelFactory
from billy.tests.fixtures.processor import DummyProcessor


class ViewTestCase(unittest.TestCase):
    
    def setUp(self):
        self.dummy_processor = DummyProcessor()

        if not hasattr(self, 'settings'):
            self.settings = {
                'billy.processor_factory': lambda: self.dummy_processor
            }

        # init database
        db_url = os.environ.get('BILLY_FUNC_TEST_DB', 'sqlite://')
        self.settings['sqlalchemy.url'] = db_url
        self.settings = setup_database({}, **self.settings)
        DeclarativeBase.metadata.bind = self.settings['engine']
        DeclarativeBase.metadata.create_all()

        app = main({}, **self.settings)
        self.testapp = TestApp(app)
        self.testapp.session = self.settings['session']

        self.dummy_request = DummyRequest()

        # create model factory
        self.model_factory = ModelFactory(
            session=self.testapp.session, 
            processor_factory=lambda: self.dummy_processor, 
            settings=self.settings,
        )

        # create all models
        self.company_model = self.model_factory.create_company_model()
        self.customer_model = self.model_factory.create_customer_model()
        self.plan_model = self.model_factory.create_plan_model()
        self.subscription_model = self.model_factory.create_subscription_model()
        self.invoice_model = self.model_factory.create_invoice_model()
        self.transaction_model = self.model_factory.create_transaction_model()
        self.transaction_failure_model = self.model_factory.create_transaction_failure_model()

    def tearDown(self):
        self.testapp.session.close()
        self.testapp.session.remove()
        DeclarativeBase.metadata.drop_all()
        self.testapp.session.bind.dispose()
