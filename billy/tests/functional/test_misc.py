from __future__ import unicode_literals

import mock
import transaction as db_transaction
from freezegun import freeze_time
from sqlalchemy.exc import IntegrityError

from billy.models import tables
from billy.tests.functional.helper import ViewTestCase


@freeze_time('2013-08-16')
class TestDBSession(ViewTestCase):

    def setUp(self):
        super(TestDBSession, self).setUp()
        with db_transaction.manager:
            self.company = self.company_model.create(
                processor_key='MOCK_PROCESSOR_KEY',
            )
        self.api_key = str(self.company.api_key)

    @mock.patch('billy.models.customer.CustomerModel.create')
    def test_db_session_is_removed(self, create_method):
        self.testapp.app.registry.settings['db_session_cleanup'] = True

        def raise_sql_error(*args, **kwargs):
            with db_transaction.manager:
                # this will raise SQL error
                customer = tables.Customer()
                self.testapp.session.add(customer)
                self.testapp.session.flush()

        create_method.side_effect = raise_sql_error
        with self.assertRaises(IntegrityError):
            self.testapp.post(
                '/v1/customers',
                extra_environ=dict(REMOTE_USER=self.api_key),
            )
        # if the session is not closed and remove correctly after a request is
        # processed, the previous SQL error will leave in session, and once 
        # we touch db session below again, it will failed and complain we 
        # didn't rollback to session
        self.testapp.get(
            '/v1/customers',
            extra_environ=dict(REMOTE_USER=self.api_key),
        )
