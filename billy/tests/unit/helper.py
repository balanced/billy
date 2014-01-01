from __future__ import unicode_literals
import os
import unittest
import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from zope.sqlalchemy import ZopeTransactionExtension

from billy.models import tables
from billy.models.company import CompanyModel
from billy.models.customer import CustomerModel
from billy.models.plan import PlanModel
from billy.models.subscription import SubscriptionModel
from billy.models.invoice import InvoiceModel
from billy.models.transaction import TransactionModel


def create_session(echo=False):
    """Create engine and session for testing, return session then
    
    """
    # NOTICE: we do all imports here because we don't want to
    # expose too many third party imports to testing modules.
    # As we want to do imports mainly in test cases.
    # In that way, import error can be captured and it won't 
    # break the whole test module

    db_url = os.environ.get('BILLY_UNIT_TEST_DB', 'sqlite:///')
    engine = create_engine(db_url, convert_unicode=True, echo=echo)
    tables.DeclarativeBase.metadata.bind = engine
    tables.DeclarativeBase.metadata.create_all()

    DBSession = scoped_session(sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
        extension=ZopeTransactionExtension()
    ))
    return DBSession


class ModelTestCase(unittest.TestCase):

    def setUp(self):
        
        self.session = create_session()
        self._old_now_func = tables.set_now_func(datetime.datetime.utcnow)

        self.company_model = CompanyModel(self.session)
        self.customer_model = CustomerModel(self.session)
        self.plan_model = PlanModel(self.session)
        self.subscription_model = SubscriptionModel(self.session)
        self.invoice_model = InvoiceModel(self.session)
        self.transaction_model = TransactionModel(self.session)

    def tearDown(self):
        self.session.remove()
        tables.DeclarativeBase.metadata.drop_all()
        self.session.bind.dispose()
        tables.set_now_func(self._old_now_func)
