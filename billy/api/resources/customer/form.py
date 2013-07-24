from __future__ import unicode_literals

from sqlalchemy.exc import *
from wtforms import Form, TextField, validators

from models import Customer
from api.errors import BillyExc


class CustomerCreateForm(Form):
    customer_id = TextField('Customer ID',
                            [validators.Required(),
                             validators.Length(min=5, max=150)])
    balanced_id = TextField('Balanced ID',
                            [validators.Required(),
                             validators.Length(min=5, max=150)])

    def save(self, group_obj):
        try:
            customer = Customer.create(external_id=self.customer_id.data,
                                       group_id=group_obj.guid,
                                       balanced_id=self.balanced_id.data)
            return customer
        except IntegrityError:
            raise BillyExc['409_CUSTOMER_ALREADY_EXISTS']
