from __future__ import unicode_literals
import datetime

import transaction as db_transaction

from billy.tests.functional.helper import ViewTestCase
from billy.api.auth import get_remote_user


class TestServerInfo(ViewTestCase):

    def make_one(self):
        return get_remote_user

    def test_server_info(self):
        res = self.testapp.get('/', status=200)
        self.assertIn('revision', res.json)

    def test_server_info_with_transaction(self):
        with db_transaction.manager:
            company = self.company_model.create(
                processor_key='MOCK_PROCESSOR_KEY',
            )
            customer = self.customer_model.create(
                company=company
            )
            plan = self.plan_model.create(
                company=company,
                frequency=self.plan_model.FREQ_WEEKLY,
                plan_type=self.plan_model.TYPE_CHARGE,
                amount=10,
            )
            subscription = self.subscription_model.create(
                customer=customer,
                plan=plan,
            )
            transaction = self.transaction_model.create(
                subscription=subscription,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=10,
                funding_instrument_uri='/v1/cards/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )

        res = self.testapp.get('/', status=200)
        self.assertEqual(res.json['last_transaction_created_at'], 
                         transaction.created_at.isoformat())
