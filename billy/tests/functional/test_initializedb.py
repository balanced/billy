from __future__ import unicode_literals
import os
import sys
import unittest
import tempfile
import shutil
import textwrap
import sqlite3
import StringIO


class TestInitializedb(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_usage(self):
        from billy.scripts import initializedb

        filename = '/path/to/initializedb'

        old_stdout = sys.stdout
        usage_out = StringIO.StringIO()
        sys.stdout = usage_out
        try:
            with self.assertRaises(SystemExit):
                initializedb.usage([filename])
        finally:
            sys.stdout = old_stdout
        expected = textwrap.dedent("""\
        usage: initializedb <config_uri>
        (example: "initializedb development.ini")
        """)
        self.assertMultiLineEqual(usage_out.getvalue(), expected)

    def test_main(self):
        from billy.scripts import initializedb
        cfg_path = os.path.join(self.temp_dir, 'config.ini')
        with open(cfg_path, 'wt') as f:
            f.write(textwrap.dedent("""\
            [app:main]
            use = egg:billy

            sqlalchemy.url = sqlite:///%(here)s/billy.sqlite
            """))
        initializedb.main([initializedb.__file__, cfg_path])

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
        ]))

    def test_main_without_enough_args(self):
        from billy.scripts import initializedb

        with self.assertRaises(SystemExit):
            initializedb.main([initializedb.__file__])
