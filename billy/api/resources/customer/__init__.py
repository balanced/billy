from __future__ import unicode_literals

from flask import request
from flask.ext.restful import marshal_with

from api.errors import BillyExc
from api.resources.group import GroupController
from models import Customer
from form import CustomerCreateForm, CustomerUpdateForm
from view import customer_view


class CustomerIndexController(GroupController):
    """
    Base customer resource used to create a customer or retrieve all your
    customers
    """

    @marshal_with(customer_view)
    def get(self):
        """
        Return a list of customers pertaining to a group
        """
        return self.group.customers

    @marshal_with(customer_view)
    def post(self):
        """
        Create a customer
        """
        customer_form = CustomerCreateForm(request.form)
        if customer_form.validate():
            return customer_form.save(self.group)
        else:
            self.form_error(customer_form.errors)


class CustomerController(GroupController):
    """
    Methods pertaining to a single customer
    """

    @marshal_with(customer_view)
    def get(self, customer_id):
        """
        Retrieve a single customer
        """
        customer = Customer.retrieve(customer_id, self.group.guid)
        if not customer:
            raise BillyExc['404_CUSTOMER_NOT_FOUND']
        return customer

    @marshal_with(customer_view)
    def put(self, customer_id):
        """
        Update a customer, currently limited to updating their coupon.
        """
        customer = Customer.retrieve(customer_id, self.group.guid)
        if not customer:
            raise BillyExc['404_CUSTOMER_NOT_FOUND']
        customer_form = CustomerUpdateForm(request.form)
        if customer_form.validate():
            return customer_form.save(customer)



