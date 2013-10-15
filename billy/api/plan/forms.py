from __future__ import unicode_literals

from wtforms import Form
from wtforms import RadioField
from wtforms import IntegerField
from wtforms import validators


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
        # TODO: what is the minimum amount limitation we have?
        validators.NumberRange(min=1)
    ])
    interval = IntegerField(
        'Interval', 
        [
            validators.Optional(),
            validators.NumberRange(min=1),
        ], 
        default=1
    )
