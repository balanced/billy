from __future__ import unicode_literals

from wtforms import Form
from wtforms import RadioField
from wtforms import IntegerField
from wtforms import validators

from billy.db import tables
from billy.api.utils import MINIMUM_AMOUNT


class EnumRadioField(RadioField):

    def __init__(self, enum_type, **kwargs):
        super(EnumRadioField, self).__init__(
            coerce=self._value_to_enum,
            **kwargs
        )
        self.enum_type = enum_type
        self.choices = [
            (enum.value.lower(), enum.description) for enum in self.enum_type
        ]

    def _value_to_enum(self, key):
        if key is None:
            return key
        return self.enum_type.from_string(key.upper())

    def pre_validate(self, form):
        for enum in self.enum_type:
            if self.data == enum:
                break
        else:
            raise ValueError(
                self.gettext('Enum of {} should be one of {}')
                .format(
                    self.enum_type.__name__,
                    list(self.enum_type.values()),
                )
            )


class PlanCreateForm(Form):
    plan_type = EnumRadioField(
        enum_type=tables.PlanType,
        label='Plan type',
        validators=[
            validators.Required(),
        ],
    )
    frequency = EnumRadioField(
        enum_type=tables.PlanFrequency,
        label='Frequency',
        validators=[
            validators.Required(),
        ],
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
