from __future__ import unicode_literals
import os
import sys
import unittest
import tempfile
import shutil
import textwrap
import StringIO

import mock
import transaction as db_transaction
from pyramid.paster import get_appsettings

from billy.models import setup_database
from billy.models.model_factory import ModelFactory
from billy.scripts import initializedb
from billy.scripts import process_transactions
from billy.scripts.process_transactions import main
from billy.tests.fixtures.processor import DummyProcessor


class TestProcessTransactions(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_usage(self):
        filename = '/path/to/process_transactions'

        old_stdout = sys.stdout
        usage_out = StringIO.StringIO()
        sys.stdout = usage_out
        try:
            with self.assertRaises(SystemExit):
                main([filename])
        finally:
            sys.stdout = old_stdout
        expected = textwrap.dedent("""\
        usage: process_transactions <config_uri>
        (example: "process_transactions development.ini")
        """)
        self.assertMultiLineEqual(usage_out.getvalue(), expected)

    @mock.patch('billy.models.transaction.TransactionModel.process_transactions')
    def test_main(self, process_transactions_method):
        cfg_path = os.path.join(self.temp_dir, 'config.ini')
        with open(cfg_path, 'wt') as f:
            f.write(textwrap.dedent("""\
            [app:main]
            use = egg:billy

            sqlalchemy.url = sqlite:///%(here)s/billy.sqlite
            billy.processor_factory = billy.models.processors.balanced_payments.BalancedProcessor
            billy.transaction.maximum_retry = 5566
            """))
        initializedb.main([initializedb.__file__, cfg_path])
        process_transactions.main([process_transactions.__file__, cfg_path])
        # ensure process_transaction method is called correctly
        process_transactions_method.assert_called_once()

    def test_main_with_crash(self):
        dummy_processor = DummyProcessor()
        dummy_processor.charge = mock.Mock()
        tx_guids = set()
        debits = []

        def mock_charge(transaction):
            if dummy_processor.charge.call_count == 2:
                raise KeyboardInterrupt
            uri = 'MOCK_DEBIT_URI_FOR_{}'.format(transaction.guid)
            if transaction.guid in tx_guids:
                return uri
            tx_guids.add(transaction.guid)
            debits.append(uri)
            return uri

        dummy_processor.charge.side_effect = mock_charge

        cfg_path = os.path.join(self.temp_dir, 'config.ini')
        with open(cfg_path, 'wt') as f:
            f.write(textwrap.dedent("""\
            [app:main]
            use = egg:billy

            sqlalchemy.url = sqlite:///%(here)s/billy.sqlite
            """))
        initializedb.main([initializedb.__file__, cfg_path])

        settings = get_appsettings(cfg_path)
        settings = setup_database({}, **settings)
        session = settings['session']
        factory = ModelFactory(
            session=session,
            processor_factory=lambda: dummy_processor,
            settings=settings,
        )
        company_model = factory.create_company_model()
        customer_model = factory.create_customer_model()
        plan_model = factory.create_plan_model()
        subscription_model = factory.create_subscription_model()

        with db_transaction.manager:
            company = company_model.create('my_secret_key')
            plan = plan_model.create(
                company=company,
                plan_type=plan_model.TYPE_CHARGE,
                amount=10,
                frequency=plan_model.FREQ_MONTHLY,
            )
            customer = customer_model.create(
                company=company,
            )
            subscription_model.create(
                customer=customer,
                plan=plan,
                funding_instrument_uri='/v1/cards/tester',
            )
            subscription_model.create(
                customer=customer,
                plan=plan,
                funding_instrument_uri='/v1/cards/tester',
            )

        with self.assertRaises(KeyboardInterrupt):
            process_transactions.main([process_transactions.__file__, cfg_path], 
                                      processor=dummy_processor)

        process_transactions.main([process_transactions.__file__, cfg_path], 
                                  processor=dummy_processor)

        # here is the story, we have two subscriptions here
        #   
        #   Subscription1
        #   Subscription2
        #
        # And the time is not advanced, so we should only have two transactions
        # to be yielded and processed. However, we assume bad thing happens
        # durring the process. We let the second call to charge of processor 
        # raises a KeyboardInterrupt error. So, it would look like this
        #
        #   charge for transaction from Subscription1
        #   charge for transaction from Subscription2 (Crash)
        #
        # Then, we perform the process_transactions again, if it works 
        # correctly, the first transaction is already yield and processed. 
        # 
        #   charge for transaction from Subscription2
        #
        # So, there would only be two charges in processor. This is mainly
        # for making sure we won't duplicate charges/payouts
        self.assertEqual(len(debits), 2)
