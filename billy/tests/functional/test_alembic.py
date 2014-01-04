from __future__ import unicode_literals
import os
import unittest
import tempfile
import textwrap
import shutil

from alembic import command
from alembic.config import Config

from billy.scripts import initializedb


class TestAlembic(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        # init database
        default_sqlite_url = 'sqlite:///{}/billy.sqlite'.format(self.temp_dir)
        self.db_url = os.environ.get(
            'BILLY_FUNC_TEST_DB', 
            default_sqlite_url,
        )
        # as these tests cannot work with in-memory sqlite, so, when it is
        # a sqlite URL, we use the one in temp folder anyway
        if self.db_url.startswith('sqlite:'):
            self.db_url = default_sqlite_url

        self.alembic_path = os.path.join(self.temp_dir, 'alembic.ini')
        with open(self.alembic_path, 'wt') as f:
            f.write(textwrap.dedent("""\
            [alembic]
            script_location = alembic
            sqlalchemy.url = {} 

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

            """).format(self.db_url))
        self.alembic_cfg = Config(self.alembic_path)

        self.cfg_path = os.path.join(self.temp_dir, 'config.ini')
        with open(self.cfg_path, 'wt') as f:
            f.write(textwrap.dedent("""\
            [app:main]
            use = egg:billy

            sqlalchemy.url = {} 
            """.format(self.db_url)))

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    @unittest.skipUnless(
        os.environ.get('BILLY_TEST_ALEMBIC'), 
        'Skip alembic database migration',
    )
    def test_downgrade_and_upgrade(self):
        initializedb.main([initializedb.__file__, self.cfg_path])
        command.stamp(self.alembic_cfg, 'head')
        command.downgrade(self.alembic_cfg, 'base')
        command.upgrade(self.alembic_cfg, 'head')
