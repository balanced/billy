from __future__ import unicode_literals

from sqlalchemy.exc import *
from wtforms import (Form, TextField, IntegerField, validators, ValidationError,
                     DateTimeField)

from models import Coupon
from api.errors import BillyExc


class CouponCreateForm(Form):
    coupon_id = TextField('Coupon ID',
                          [validators.Required(),
                           validators.Length(min=5, max=150)])
    name = TextField('Name',
                     [validators.Required(),
                      validators.Length(min=3, max=150)])

    price_off_cents = IntegerField('Price off cents', [validators.Required()])

    percent_off_int = IntegerField('Percent off', [validators.Required()])

    max_redeem = IntegerField('Max Redemptions')

    repeating = IntegerField('Repeating')

    expire_at = DateTimeField('Expire at', default=None)


    def validate_max_redeem(self, field):
        if not (field.data > 0 or field.data == -1):
            raise ValidationError('max_redeem must be -1 or greater than 0')

    def validate_repeating(self, field):
        if not (field.data > 0 or field.data == -1):
            raise ValidationError('repeating must be -1 or greater than 0')

    def validate_percent_off_int(self, field):
        if not 0 <= field.data <= 100:
            raise ValidationError('percent_off_int must be between 0 and 100')

    def validate_price_off_cents(self, field):
        if not field.data >= 0:
            raise ValidationError('price_off_cents must be between >= 0')


    def save(self, group_obj):
        try:
            coupon = Coupon.create(external_id=self.coupon_id.data,
                                   group_id=group_obj.guid,
                                   name=self.name.data,
                                   price_off_cents=self.price_off_cents.data,
                                   percent_off_int=self.percent_off_int.data,
                                   max_redeem=self.max_redeem.data,
                                   repeating=self.repeating.data,
            )
            return coupon
        except IntegrityError:
            raise BillyExc['409_COUPON_ALREADY_EXISTS']
