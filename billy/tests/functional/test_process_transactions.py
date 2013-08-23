from __future__ import unicode_literals
import os
import sys
import unittest
import tempfile
import shutil
import textwrap
import StringIO

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
        import balanced
        from billy.models.transaction import TransactionModel
        from billy.scripts import initializedb
        from billy.scripts import process_transactions

        (
            flexmock(balanced)
            .should_receive('configure')
            .with_args('MOCK_BALANCED_API_KEY')
            .once()
        )

        (
            flexmock(TransactionModel)
            .should_receive('process_transactions')
            .once()
        )

        cfg_path = os.path.join(self.temp_dir, 'config.ini')
        with open(cfg_path, 'wt') as f:
            f.write(textwrap.dedent("""\
            [app:main]
            use = egg:billy

            sqlalchemy.url = sqlite:///%(here)s/billy.sqlite

            balanced.api_key = MOCK_BALANCED_API_KEY
            """))
        initializedb.main([initializedb.__file__, cfg_path])
        process_transactions.main([process_transactions.__file__, cfg_path])
        # TODO: do more check here?
