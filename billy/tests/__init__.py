from __future__ import unicode_literals
import unittest
import os

import sqlalchemy

from billy.settings import DB_URL, Session
from billy.models.base import Base

BASE_PATH = os.path.abspath(os.path.join(
    os.path.basename(__file__), '..'))
SCRIPTS_PATH = os.path.join(BASE_PATH, 'scripts')
PACKAGE_PATH = os.path.join(BASE_PATH, 'balanced_service')



class BalancedTransactionalTestCase(unittest.TestCase):
    """
    This class is optimized for multiple tests requiring the
    database, by putting every db test in a large transaction
    avoiding the commit to the database, significantly speeding
    up tests by order of magnitudes.

    The one thing that is hard to test with this class though is
    the updateon or trigger tests. For that reason, if needed, it
    might be more beneficial to use the BalancedSlowDBTestCase class
    below.
    """



    def __init__(self, *A, **KW):
        super(BalancedTransactionalTestCase, self).__init__(*A, **KW)
        self._db_engine = sqlalchemy.create_engine(DB_URL,
            isolation_level='SERIALIZABLE'
        )

    def setUp(self):
        super(BalancedTransactionalTestCase, self).setUp()

        self._db_connection = self._db_engine.connect()
        self._db_transaction = self._db_connection.begin()
        Session.configure(bind=self._db_connection)
        # HACK: this is done solely to set up signals for model test cases --
        # alternatives are welcome
        self.session = Base.session = Session
        Base.session.commit = Base.session.flush
        # adds the clean up handler that will reset the database
        # state, which is necessary for when your setUp() function
        # can fail in the middle of setting up a db-fixture.
        # if we don't do this, then the transaction is never closed,
        # causing a deadlock
        self.addCleanup(_transactional_db_reset,
                        db_session=self.session,
                        db_transaction=self._db_transaction,
                        db_connection=self._db_connection)


def _transactional_db_reset(db_session, db_transaction, db_connection):
    # roll it back
    db_session.rollback()
    # expunge the entire session
    db_session.expunge_all()
    # clean up the transaction
    db_transaction.close()
    # you must detach the connection or otherwise,
    # you have lingering connections that will keep an open
    # connection.
    db_connection.detach()
    db_connection.close()
    # remove the session from the registry
    Session.remove()
