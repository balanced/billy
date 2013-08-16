from __future__ import unicode_literals
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
    engine = create_engine('sqlite:///', convert_unicode=True, echo=echo)
    DeclarativeBase.metadata.bind = engine
    DeclarativeBase.metadata.create_all(bind=engine)

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
        from billy.tests.helper import create_session
        self.session = create_session()
        self.now = datetime.datetime.utcnow()
        self._old_now_func = tables.set_now_func(lambda: self.now)

    def tearDown(self):
        from billy.models import tables
        self.session.remove()
        tables.set_now_func(self._old_now_func)
