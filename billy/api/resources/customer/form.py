from __future__ import unicode_literals

from sqlalchemy.exc import *
from wtforms import Form, TextField, validators

from models import Customer
from api.errors import BillyExc


class CustomerCreateForm(Form):
    customer_id = TextField('Customer ID',
                            [validators.Required(),
                             validators.Length(min=5, max=150)])
    provider_id = TextField('Balanced ID',
                            [validators.Required(),
                             validators.Length(min=5, max=150)])

    def save(self, group_obj):
        try:
            customer = Customer.create(your_id=self.customer_id.data,
                                       group_id=group_obj.id,
                                       provider_id=self.provider_id.data)
            return customer
        except IntegrityError:
            raise BillyExc['409_CUSTOMER_ALREADY_EXISTS']


class CustomerUpdateForm(Form):
    coupon_id = TextField('Coupon ID')

    def save(self, customer):
        try:
            return customer.apply_coupon(self.coupon_id.data)
        except ValueError:
            raise BillyExc['409_COUPON_MAX_REDEEM']
        except NameError:
            raise BillyExc['404_COUPON_NOT_FOUND']
