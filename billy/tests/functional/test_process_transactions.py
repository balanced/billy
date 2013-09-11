from __future__ import unicode_literals
import os
import sys
import unittest
import tempfile
import shutil
import textwrap
import StringIO

import transaction as db_transaction
from flexmock import flexmock


class TestProcessTransactions(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_usage(self):
        from billy.scripts.process_transactions import main

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

    def test_main(self):
        from billy.models.transaction import TransactionModel
        from billy.models.processors.balanced_payments import BalancedProcessor
        from billy.scripts import initializedb
        from billy.scripts import process_transactions

        def mock_process_transactions(processor, maximum_retry):
            self.assertIsInstance(processor, BalancedProcessor)
            self.assertEqual(maximum_retry, 5566)

        (
            flexmock(TransactionModel)
            .should_receive('process_transactions')
            .replace_with(mock_process_transactions)
            .once()
        )

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
        # TODO: do more check here?

    def test_main_with_crash(self):
        from pyramid.paster import get_appsettings
        from billy.models import setup_database
        from billy.models.company import CompanyModel
        from billy.models.customer import CustomerModel
        from billy.models.plan import PlanModel
        from billy.models.subscription import SubscriptionModel
        from billy.scripts import initializedb
        from billy.scripts import process_transactions

        class MockProcessor(object):

            def __init__(self):
                self.charges = {}
                self.tx_sn = 0
                self.called_times = 0

            def create_customer(self, customer):
                return 'MOCK_PROCESSOR_CUSTOMER_ID'

            def prepare_customer(self, customer, payment_uri=None):
                pass

            def charge(self, transaction):
                self.called_times += 1
                if self.called_times == 2:
                    raise KeyboardInterrupt
                guid = transaction.guid
                if guid in self.charges:
                    return self.charges[guid]
                self.charges[guid] = self.tx_sn
                self.tx_sn += 1

        mock_processor = MockProcessor()
        
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
        company_model = CompanyModel(session)
        customer_model = CustomerModel(session)
        plan_model = PlanModel(session)
        subscription_model = SubscriptionModel(session)

        with db_transaction.manager:
            company_guid = company_model.create('my_secret_key')
            plan_guid = plan_model.create(
                company_guid=company_guid,
                plan_type=plan_model.TYPE_CHARGE,
                amount=10,
                frequency=plan_model.FREQ_MONTHLY,
            )
            customer_guid = customer_model.create(
                company_guid=company_guid,
            )
            subscription_model.create(
                customer_guid=customer_guid,
                plan_guid=plan_guid,
                payment_uri='/v1/cards/tester',
            )
            subscription_model.create(
                customer_guid=customer_guid,
                plan_guid=plan_guid,
                payment_uri='/v1/cards/tester',
            )

        with self.assertRaises(KeyboardInterrupt):
            process_transactions.main([process_transactions.__file__, cfg_path], 
                                      processor=mock_processor)

        process_transactions.main([process_transactions.__file__, cfg_path], 
                                  processor=mock_processor)

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
        self.assertEqual(len(mock_processor.charges), 2)
