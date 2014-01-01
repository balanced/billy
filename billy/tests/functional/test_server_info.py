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
            company_guid = self.company_model.create(
                processor_key='MOCK_PROCESSOR_KEY',
            )
            customer_guid = self.customer_model.create(
                company_guid=company_guid
            )
            plan_guid = self.plan_model.create(
                company_guid=company_guid,
                frequency=self.plan_model.FREQ_WEEKLY,
                plan_type=self.plan_model.TYPE_CHARGE,
                amount=10,
            )
            subscription_guid = self.subscription_model.create(
                customer_guid=customer_guid,
                plan_guid=plan_guid,
            )
            transaction_guid = self.transaction_model.create(
                subscription_guid=subscription_guid,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=10,
                payment_uri='/v1/cards/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )

        transaction = self.transaction_model.get(transaction_guid)

        res = self.testapp.get('/', status=200)
        self.assertEqual(res.json['last_transaction_created_at'], 
                         transaction.created_at.isoformat())
