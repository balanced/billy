from __future__ import unicode_literals

from flask import request
from flask.ext.restful import marshal_with

from api.errors import BillyExc
from api.resources.group import GroupController
from models import Customer
from form import CustomerCreateForm
from view import customer_view


class CustomerIndexController(GroupController):
    def get(self):
        return self.group.customers


class CustomerController(CustomerIndexController):
    customer = None

    def __init__(self):
        super(CustomerController, self).__init__()
        self.pull_customer_object()

    def pull_customer_object(self):
        customer_id = self.param_from_request('customer_id')
        self.customer = Customer.retrieve(customer_id, self.group.guid)
        if request.method in ['GET', 'PUT'] and not self.customer:
            raise BillyExc['404_CUSTOMER_NOT_FOUND']
        if request.method == 'POST' and self.customer:
            raise BillyExc['409_CUSTOMER_ALREADY_EXISTS']


    @marshal_with(customer_view)
    def get(self, customer_id):
        import ipdb;ipdb.set_trace()
        return self.customer

    @marshal_with(customer_view)
    def post(self, customer_id):
        customer_form = CustomerCreateForm(request.form,
                                           customer_id=customer_id)
        if customer_form.validate():
            return customer_form.save(self.group)
        else:
            if customer_form.errors.get('customer_id'):
                raise BillyExc['400_CUSTOMER_ID']
            else:
                raise BillyExc['400']

