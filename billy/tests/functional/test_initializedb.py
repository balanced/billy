from __future__ import unicode_literals
import os
import sys
import unittest
import tempfile
import shutil
import textwrap
import sqlite3
import StringIO

from billy.scripts import initializedb


class TestInitializedb(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_usage(self):

        filename = '/path/to/initializedb'

        old_stdout = sys.stdout
        usage_out = StringIO.StringIO()
        sys.stdout = usage_out
        try:
            with self.assertRaises(SystemExit):
                initializedb.main([filename])
        finally:
            sys.stdout = old_stdout
        expected = textwrap.dedent("""\
        usage: initializedb <config_uri> [alembic_uri]
        (example: "initializedb development.ini alembic.ini")
        """)
        self.assertMultiLineEqual(usage_out.getvalue(), expected)

    def test_main(self):
        cfg_path = os.path.join(self.temp_dir, 'config.ini')
        with open(cfg_path, 'wt') as f:
            f.write(textwrap.dedent("""\
            [app:main]
            use = egg:billy

            sqlalchemy.url = sqlite:///%(here)s/billy.sqlite
            """))

        alembic_path = os.path.join(self.temp_dir, 'alembic.ini')
        with open(alembic_path, 'wt') as f:
            f.write(textwrap.dedent("""\
            [alembic]
            script_location = alembic
            sqlalchemy.url = sqlite:///%(here)s/billy.sqlite

            [loggers]
            keys = root

            [handlers]
            keys =

            [formatters]
            keys =

            [logger_root]
            level = WARN
            qualname =
            handlers =

            """))

        initializedb.main([initializedb.__file__, cfg_path, alembic_path])

        sqlite_path = os.path.join(self.temp_dir, 'billy.sqlite')
        self.assertTrue(os.path.exists(sqlite_path))

        conn = sqlite3.connect(sqlite_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        self.assertEqual(set(tables), set([
            'company',
            'customer',
            'plan',
            'subscription',
            'transaction',
            'transaction_event',
            'transaction_failure',
            'customer_invoice',
            'subscription_invoice',
            'invoice',
            'item',
            'adjustment',
            'alembic_version',
        ]))

        # make sure we have an alembic version there
        cursor.execute("SELECT * FROM alembic_version;")
        version = cursor.fetchone()[0]
        self.assertNotEqual(version, None)
