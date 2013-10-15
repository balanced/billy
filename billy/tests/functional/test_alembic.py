from __future__ import unicode_literals
import os
import unittest
import tempfile
import textwrap
import decimal
import shutil

import transaction as db_transaction


class TestAlembic(unittest.TestCase):

    def setUp(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import scoped_session
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.ext.declarative import declarative_base
        from zope.sqlalchemy import ZopeTransactionExtension
        from alembic.config import Config
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
        self.engine = create_engine(self.db_url, convert_unicode=True)
        self.declarative_base = declarative_base()
        self.declarative_base.metadata.bind = self.engine

        self.session = scoped_session(sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
            extension=ZopeTransactionExtension()
        ))

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

    def tearDown(self):
        # drop all tables
        self.session.remove()
        self.declarative_base.metadata.drop_all()
        shutil.rmtree(self.temp_dir)

    def test_use_integer_column_for_amount(self):
        from sqlalchemy import Column
        from sqlalchemy import Integer
        from sqlalchemy import Numeric

        class Plan(self.declarative_base):
            __tablename__ = 'plan'
            guid = Column(Integer, primary_key=True)
            amount = Column(Numeric(10, 2))

        class Subscription(self.declarative_base):
            __tablename__ = 'subscription'
            guid = Column(Integer, primary_key=True)
            amount = Column(Numeric(10, 2))

        class Transaction(self.declarative_base):
            __tablename__ = 'transaction'
            guid = Column(Integer, primary_key=True)
            amount = Column(Numeric(10, 2))

        self.declarative_base.metadata.create_all()

        with db_transaction.manager:
            for amount in ['12.34', '55.66', '10']:
                amount = decimal.Decimal(amount)
                plan = Plan(amount=amount)
                subscription = Subscription(amount=amount)
                transaction = Transaction(amount=amount)
                self.session.add(plan)
                self.session.add(subscription)
                self.session.add(transaction)

        from alembic import command
        command.stamp(self.alembic_cfg, 'base')

        command.upgrade(self.alembic_cfg, 'b3d4192b123')
        for table in [Plan, Subscription, Transaction]:
            amounts = self.session.query(table.amount).all()
            amounts = map(lambda item: float(item[0]), amounts)
            # make sure all float dollars are converted into integer cents
            self.assertEqual(set(amounts), set([1234, 5566, 1000]))

        command.downgrade(self.alembic_cfg, 'base')
        for table in [Plan, Subscription, Transaction]:
            amounts = self.session.query(table.amount).all()
            amounts = map(lambda item: item[0], amounts)
            self.assertEqual(
                set(amounts), 
                set(map(decimal.Decimal, ['12.34', '55.66', '10']))
            )
