"""Add transaction failure table

Revision ID: 3c76fb0d6937
Revises: 54e1d07a2512
Create Date: 2014-01-04 18:30:51.937000

"""

# revision identifiers, used by Alembic.
revision = '3c76fb0d6937'
down_revision = '54e1d07a2512'

from alembic import op
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import Unicode
from sqlalchemy import UnicodeText
from sqlalchemy import DateTime
from sqlalchemy.sql import table
from sqlalchemy.sql import select
from sqlalchemy.schema import ForeignKey


transaction = table(
    'transaction',
    Column('guid', Unicode(64), primary_key=True),
    Column('error_message', UnicodeText),
    Column('failure_count', Integer),
    Column('created_at', DateTime),
) 


transaction_failure = table(
    'transaction_failure',
    Column('guid', Unicode(64), primary_key=True),
    Column('transaction_guid', Unicode(64)),
    Column('error_message', UnicodeText),
    Column('created_at', DateTime),
) 


def upgrade():
    op.create_table(
        'transaction_failure',
        Column('guid', Unicode(64), primary_key=True),
        Column(
            'transaction_guid',
            Unicode(64), 
            ForeignKey(
                'transaction.guid', 
                ondelete='CASCADE', onupdate='CASCADE'
            ), 
            index=True,
            nullable=False,
        ),
        Column('error_message', UnicodeText),
        Column('error_number', Integer),
        Column('error_code', Unicode(64)),
        Column('created_at', DateTime),
    )

    op.execute((
        transaction_failure.insert()
        .from_select(
            ['guid', 'transaction_guid', 'error_message', 'created_at'], 
            select([
                transaction.c.guid.label('TF_ID'),
                transaction.c.guid.label('TX_ID'),
                transaction.c.error_message, 
                transaction.c.created_at, 
            ])
        )
    ))
    # ouch.. SQLlite doens't support alter column syntax,
    bind = op.get_bind()
    if bind is None or bind.engine.name != 'sqlite':
        op.drop_column('transaction', 'error_message')
        op.drop_column('transaction', 'failure_count')


def downgrade():
    op.drop_table('transaction_failure')
    # ouch.. SQLlite doens't support alter column syntax,
    bind = op.get_bind()
    if bind is None or bind.engine.name != 'sqlite':
        op.add_column('transaction', Column('error_message', UnicodeText))
        op.add_column('transaction', Column('failure_count', Integer))
