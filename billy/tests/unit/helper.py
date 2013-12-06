from __future__ import unicode_literals
import os
import unittest
import datetime


def create_session(echo=False):
    """Create engine and session for testing, return session then
    
    """
    # NOTICE: we do all imports here because we don't want to
    # expose too many third party imports to testing modules.
    # As we want to do imports mainly in test cases.
    # In that way, import error can be captured and it won't 
    # break the whole test module
    from sqlalchemy import create_engine
    from sqlalchemy.orm import scoped_session
    from sqlalchemy.orm import sessionmaker
    from zope.sqlalchemy import ZopeTransactionExtension
    from billy.models.tables import DeclarativeBase
    db_url = os.environ.get('BILLY_UNIT_TEST_DB', 'sqlite:///')
    engine = create_engine(db_url, convert_unicode=True, echo=echo)
    DeclarativeBase.metadata.bind = engine
    DeclarativeBase.metadata.create_all()

    DBSession = scoped_session(sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
        extension=ZopeTransactionExtension()
    ))
    return DBSession


class ModelTestCase(unittest.TestCase):

    def setUp(self):
        from billy.models import tables
        self.session = create_session()
        self._old_now_func = tables.set_now_func(datetime.datetime.utcnow)

    def tearDown(self):
        from billy.models import tables
        self.session.remove()
        self.session.bind.dispose()
        tables.DeclarativeBase.metadata.drop_all()
        tables.set_now_func(self._old_now_func)
