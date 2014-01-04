"""Change column name

Revision ID: 54e1d07a2512
Revises: b3d4192b123
Create Date: 2014-01-04 18:17:28.074000

"""

# revision identifiers, used by Alembic.
revision = '54e1d07a2512'
down_revision = 'b3d4192b123'

from alembic import op


def upgrade():
    # ouch.. SQLlite doens't support alter column syntax,
    bind = op.get_bind()
    if bind is None or bind.engine.name != 'sqlite':
        op.alter_column(
            'customer', 
            column_name='external_id', 
            new_column_name='processor_uri',
        )
        op.alter_column(
            'transaction', 
            column_name='external_id', 
            new_column_name='processor_uri',
        )
        op.alter_column(
            'transaction', 
            column_name='payment_uri', 
            new_column_name='funding_instrument_uri',
        )


def downgrade():
    # ouch.. SQLlite doens't support alter column syntax,
    bind = op.get_bind()
    if bind is None or bind.engine.name != 'sqlite':
        op.alter_column(
            'customer', 
            column_name='processor_uri', 
            new_column_name='external_id',
        )
        op.alter_column(
            'transaction', 
            column_name='processor_uri', 
            new_column_name='external_id',
        )
        op.alter_column(
            'transaction', 
            column_name='funding_instrument_uri', 
            new_column_name='payment_uri',
        )
