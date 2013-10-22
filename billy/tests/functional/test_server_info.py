from __future__ import unicode_literals
import datetime

import transaction as db_transaction

from billy.tests.functional.helper import ViewTestCase


class TestServerInfo(ViewTestCase):

    def make_one(self):
        from billy.api.auth import get_remote_user
        return get_remote_user

    def test_server_info(self):
        res = self.testapp.get('/', status=200)
        self.assertIn('revision', res.json)

    def test_server_info_with_transaction(self):
        from billy.models.company import CompanyModel
        from billy.models.customer import CustomerModel
        from billy.models.plan import PlanModel
        from billy.models.subscription import SubscriptionModel
        from billy.models.transaction import TransactionModel

        company_model = CompanyModel(self.testapp.session)
        customer_model = CustomerModel(self.testapp.session)
        plan_model = PlanModel(self.testapp.session)
        subscription_model = SubscriptionModel(self.testapp.session)
        transaction_model = TransactionModel(self.testapp.session)

        with db_transaction.manager:
            company_guid = company_model.create(
                processor_key='MOCK_PROCESSOR_KEY',
            )
            customer_guid = customer_model.create(
                company_guid=company_guid
            )
            plan_guid = plan_model.create(
                company_guid=company_guid,
                frequency=plan_model.FREQ_WEEKLY,
                plan_type=plan_model.TYPE_CHARGE,
                amount=10,
            )
            subscription_guid = subscription_model.create(
                customer_guid=customer_guid,
                plan_guid=plan_guid,
            )
            transaction_guid = transaction_model.create(
                subscription_guid=subscription_guid,
                transaction_cls=transaction_model.CLS_SUBSCRIPTION,
                transaction_type=transaction_model.TYPE_CHARGE,
                amount=10,
                payment_uri='/v1/cards/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )

        transaction = transaction_model.get(transaction_guid)

        res = self.testapp.get('/', status=200)
        self.assertEqual(res.json['last_transaction_created_at'], 
                         transaction.created_at.isoformat())
