"""Use integer column for amount

Revision ID: b3d4192b123
Revises: None
Create Date: 2013-10-15 11:42:53.334742

"""

# revision identifiers, used by Alembic.
revision = 'b3d4192b123'
down_revision = None

import decimal
from alembic import op
from sqlalchemy.sql import column
from sqlalchemy.sql import table
from sqlalchemy import Numeric
from sqlalchemy import Integer


plan = table(
    'plan',
    column('amount', Numeric(10, 2))
)
subscription = table(
    'subscription',
    column('amount', Numeric(10, 2))
)
transaction = table(
    'transaction',
    column('amount', Numeric(10, 2))
)


def upgrade():
    # update all amount values from like 12.34 to 1234
    op.execute(
        plan.update().values(dict(amount=plan.c.amount * 100))
    )
    op.execute(
        subscription.update().values(dict(amount=subscription.c.amount * 100))
    )
    op.execute(
        transaction.update().values(dict(amount=transaction.c.amount * 100))
    )
    # ouch.. SQLlite doens't support alter column syntax,
    bind = op.get_bind()
    if bind is None or bind.engine.name != 'sqlite':
        # modify the column from Numeric to Integer
        op.alter_column('plan', 'amount', type_=Integer)
        op.alter_column('subscription', 'amount', type_=Integer)
        op.alter_column('transaction', 'amount', type_=Integer)


def downgrade():
    # ouch.. SQLlite doens't support alter column syntax,
    bind = op.get_bind()
    if bind is None or bind.engine.name != 'sqlite':
        # modify the column from Integer to Numeric
        op.alter_column('plan', 'amount', type_=Numeric(10, 2))
        op.alter_column('subscription', 'amount', type_=Numeric(10, 2))
        op.alter_column('transaction', 'amount', type_=Numeric(10, 2))
    # update all amount values from like 12.34 to 1234
    num = decimal.Decimal('100')
    op.execute(
        plan.update().values(dict(amount=plan.c.amount / num))
    )
    op.execute(
        subscription.update().values(dict(amount=subscription.c.amount / num))
    )
    op.execute(
        transaction.update().values(dict(amount=transaction.c.amount / num))
    )
