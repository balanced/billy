from __future__ import unicode_literals

from sqlalchemy.exc import *
from wtforms import (
    Form, TextField, IntegerField, validators, ValidationError,
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
        except ValueError, e:
            raise BillyExc[e.message]  # ERROR code passed by model.


class CouponUpdateForm(Form):
    name = TextField('Name',
                     [validators.Length(min=3, max=150)], default=None)

    max_redeem = IntegerField('Max Redemptions', default=None)

    repeating = IntegerField('Repeating', default=None)

    expire_at = DateTimeField('Expire at', default=None)

    def save(self, coupon):
        try:
            return coupon.update(new_name=self.name.data,
                                 new_max_redeem=self.max_redeem.data,
                                 new_expire_at=self.expire_at.data,
                                 new_repeating=self.repeating.data)
        except ValueError, e:
            raise BillyExc[e.message]
