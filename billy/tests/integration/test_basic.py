from __future__ import unicode_literals

import balanced

from billy.tests.integration.helper import IntegrationTestCase


class TestBasicScenarios(IntegrationTestCase):

    def test_simple_subscription_and_cancel(self):
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
                plan_type='debit',
                amount=1234,
                frequency='daily',
            ),
            headers=[self.make_auth(api_key)],
            status=200
        )
        plan = res.json
        self.assertEqual(plan['plan_type'], 'debit')
        self.assertEqual(plan['amount'], 1234)
        self.assertEqual(plan['frequency'], 'daily')
        self.assertEqual(plan['company_guid'], company['guid'])

        # create a subscription
        res = self.testapp.post(
            '/v1/subscriptions',
            dict(
                customer_guid=customer['guid'],
                plan_guid=plan['guid'],
                funding_instrument_uri=card.uri,
                appears_on_statement_as='hello baby',
            ),
            headers=[self.make_auth(api_key)],
            status=200
        )
        subscription = res.json
        self.assertEqual(subscription['customer_guid'], customer['guid'])
        self.assertEqual(subscription['plan_guid'], plan['guid'])
        self.assertEqual(subscription['appears_on_statement_as'], 'hello baby')

        # get invoice
        res = self.testapp.get(
            '/v1/subscriptions/{}/invoices'.format(subscription['guid']),
            headers=[self.make_auth(api_key)],
            status=200
        )
        invoices = res.json
        self.assertEqual(len(invoices['items']), 1)
        invoice = res.json['items'][0]
        self.assertEqual(invoice['subscription_guid'], subscription['guid'])
        self.assertEqual(invoice['status'], 'settled')

        # transactions
        res = self.testapp.get(
            '/v1/transactions',
            headers=[self.make_auth(api_key)],
            status=200
        )
        transactions = res.json
        self.assertEqual(len(transactions['items']), 1)
        transaction = res.json['items'][0]
        self.assertEqual(transaction['invoice_guid'], invoice['guid'])
        self.assertEqual(transaction['status'], 'done')
        self.assertEqual(transaction['transaction_type'], 'debit')
        self.assertEqual(transaction['appears_on_statement_as'], 'hello baby')

        debit = balanced.Debit.find(transaction['processor_uri'])
        self.assertEqual(debit.meta['billy.transaction_guid'], transaction['guid'])
        self.assertEqual(debit.amount, 1234)
        self.assertEqual(debit.status, 'succeeded')
        self.assertEqual(debit.appears_on_statement_as, 'hello baby')

        # cancel the subscription
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

        # refund the invoice
        self.testapp.post(
            '/v1/invoices/{}/refund'.format(invoice['guid']),
            dict(
                amount=1234,
            ),
            headers=[self.make_auth(api_key)],
            status=200
        )

        # get transactions
        res = self.testapp.get(
            '/v1/transactions',
            headers=[self.make_auth(api_key)],
            status=200
        )
        transactions = res.json
        self.assertEqual(len(transactions['items']), 2)
        transaction = res.json['items'][0]
        self.assertEqual(transaction['invoice_guid'], invoice['guid'])
        self.assertEqual(transaction['status'], 'done')
        self.assertEqual(transaction['transaction_type'], 'refund')

        refund = balanced.Refund.find(transaction['processor_uri'])
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

    def test_invoicing(self):
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

        # create an invoice
        res = self.testapp.post(
            '/v1/invoices',
            dict(
                customer_guid=customer['guid'],
                amount=5566,
                title='Awesome invoice',
                item_name1='Foobar',
                item_amount1=200,
                adjustment_amount1='123',
                adjustment_reason1='tips',
                funding_instrument_uri=card.uri,
                appears_on_statement_as='hello baby',
            ),
            headers=[self.make_auth(api_key)],
            status=200
        )
        invoice = res.json
        self.assertEqual(invoice['title'], 'Awesome invoice')
        self.assertEqual(invoice['amount'], 5566)
        self.assertEqual(invoice['effective_amount'], 5566 + 123)
        self.assertEqual(invoice['status'], 'settled')
        self.assertEqual(invoice['appears_on_statement_as'], 'hello baby')

        # transactions
        res = self.testapp.get(
            '/v1/transactions',
            headers=[self.make_auth(api_key)],
            status=200
        )
        transactions = res.json
        self.assertEqual(len(transactions['items']), 1)
        transaction = res.json['items'][0]
        self.assertEqual(transaction['invoice_guid'], invoice['guid'])
        self.assertEqual(transaction['status'], 'done')
        self.assertEqual(transaction['transaction_type'], 'debit')
        self.assertEqual(transaction['appears_on_statement_as'], 'hello baby')

        debit = balanced.Debit.find(transaction['processor_uri'])
        self.assertEqual(debit.meta['billy.transaction_guid'], transaction['guid'])
        self.assertEqual(debit.amount, 5566 + 123)
        self.assertEqual(debit.status, 'succeeded')
        self.assertEqual(debit.appears_on_statement_as, 'hello baby')

    def test_invalid_funding_instrument(self):
        balanced.configure(self.processor_key)
        marketplace = balanced.Marketplace.find(self.marketplace_uri)
        # create a card
        card = marketplace.create_card(
            name='BILLY_INTERGRATION_TESTER',
            card_number='5105105105105100',
            expiration_month='12',
            expiration_year='2020',
            security_code='123',
        )
        card_uri = card.uri
        card.is_valid = False
        card.save()

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

        # create an invoice
        res = self.testapp.post(
            '/v1/invoices',
            dict(
                customer_guid=customer['guid'],
                amount=5566,
                funding_instrument_uri=card_uri,
            ),
            headers=[self.make_auth(api_key)],
            status=400
        )
        self.assertEqual(res.json['error_class'], 'InvalidFundingInstrument')
