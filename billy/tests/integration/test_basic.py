from __future__ import unicode_literals

from billy.tests.integration.helper import IntegrationTestCase


class TestBasicScenarios(IntegrationTestCase):

    def test_simple_subscription_and_cancel(self):
        import balanced
        balanced.configure(self.processor_key)
        marketplace = balanced.Marketplace.find(self.marketplace_uri)

        # create a card to charge
        card = marketplace.create_card(
            name='BILLY_INTERGRATION_TESTER',
            card_number='5105105105105100',
            expiration_month='12',
            expiration_year='2020',
            security_code='123',
        )

        # create a company
        res = self.testapp.post(
            '/v1/companies', 
            dict(processor_key=self.processor_key), 
            status=200
        )
        company = res.json
        api_key = str(company['api_key'])

        # create a customer
        res = self.testapp.post(
            '/v1/customers', 
            headers=[self.make_auth(api_key)],
            status=200
        )
        customer = res.json
        self.assertEqual(customer['company_guid'], company['guid'])

        # create a plan
        res = self.testapp.post(
            '/v1/plans', 
            dict(
                plan_type='charge',
                amount=1234,
                frequency='daily',
            ),
            headers=[self.make_auth(api_key)],
            status=200
        )
        plan = res.json
        self.assertEqual(plan['plan_type'], 'charge')
        self.assertEqual(plan['amount'], 1234)
        self.assertEqual(plan['frequency'], 'daily')
        self.assertEqual(plan['company_guid'], company['guid'])

        # create a subscription
        res = self.testapp.post(
            '/v1/subscriptions', 
            dict(
                customer_guid=customer['guid'],
                plan_guid=plan['guid'],
                payment_uri=card.uri,
            ),
            headers=[self.make_auth(api_key)],
            status=200
        )
        subscription = res.json
        self.assertEqual(subscription['customer_guid'], customer['guid'])
        self.assertEqual(subscription['plan_guid'], plan['guid'])

        # transactions
        res = self.testapp.get(
            '/v1/transactions', 
            headers=[self.make_auth(api_key)],
            status=200
        )
        transactions = res.json
        self.assertEqual(len(transactions['items']), 1)
        transaction = res.json['items'][0]
        self.assertEqual(transaction['subscription_guid'], subscription['guid'])
        self.assertEqual(transaction['status'], 'done')
        self.assertEqual(transaction['transaction_type'], 'charge')

        debit = balanced.Debit.find(transaction['external_id'])
        self.assertEqual(debit.meta['billy.transaction_guid'], transaction['guid'])
        self.assertEqual(debit.amount, 1234)
        self.assertEqual(debit.status, 'succeeded')

        # cancel the subscription and refund
        res = self.testapp.post(
            '/v1/subscriptions/{}/cancel'.format(subscription['guid']), 
            dict(
                refund_amount=1234,
            ),
            headers=[self.make_auth(api_key)],
            status=200
        )
        subscription = res.json
        self.assertEqual(subscription['canceled'], True)

        # get transactions
        res = self.testapp.get(
            '/v1/transactions', 
            headers=[self.make_auth(api_key)],
            status=200
        )
        transactions = res.json
        self.assertEqual(len(transactions['items']), 2)
        transaction = res.json['items'][0]
        self.assertEqual(transaction['subscription_guid'], subscription['guid'])
        self.assertEqual(transaction['status'], 'done')
        self.assertEqual(transaction['transaction_type'], 'refund')

        refund = balanced.Debit.find(transaction['external_id'])
        self.assertEqual(refund.meta['billy.transaction_guid'], 
                         transaction['guid'])
        self.assertEqual(refund.amount, 1234)
        self.assertEqual(refund.status, 'succeeded')

        # delete the plan
        res = self.testapp.delete(
            '/v1/plans/{}'.format(plan['guid']), 
            headers=[self.make_auth(api_key)],
            status=200
        )
        plan = res.json
        self.assertEqual(plan['deleted'], True)

        # delete the customer
        res = self.testapp.delete(
            '/v1/customers/{}'.format(customer['guid']), 
            headers=[self.make_auth(api_key)],
            status=200
        )
        customer = res.json
        self.assertEqual(customer['deleted'], True)
