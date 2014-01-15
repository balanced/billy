from __future__ import unicode_literals

from wtforms import Form
from wtforms import RadioField
from wtforms import IntegerField
from wtforms import validators

from billy.api.utils import MINIMUM_AMOUNT


class PlanCreateForm(Form):
    plan_type = RadioField(
        'Plan type',
        [
            validators.Required(),
        ],
        choices=[
            ('charge', 'Charge'),
            ('payout', 'Payout'),
        ]
    )
    frequency = RadioField(
        'Frequency',
        [
            validators.Required(),
        ],
        choices=[
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
            ('yearly', 'Yearly'),
        ]
    )
    amount = IntegerField('Amount', [
        validators.Required(),
        validators.NumberRange(min=MINIMUM_AMOUNT)
    ])
    interval = IntegerField(
        'Interval',
        [
            validators.Optional(),
            validators.NumberRange(min=1),
        ],
        default=1
    )
