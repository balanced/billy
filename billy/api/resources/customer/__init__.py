from __future__ import unicode_literals

from flask import request
from flask.ext.restful import marshal_with

from billy.api.errors import BillyExc
from billy.api.resources.group import GroupController
from billy.models import Customer
from .form import CustomerCreateForm, CustomerUpdateForm
from .view import customer_view


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
            return customer_form.save(self.group), 201
        else:
            self.form_error(customer_form.errors)


class CustomerController(GroupController):

    """
    Methods pertaining to a single customer
    """

    def __init__(self):
        super(CustomerController, self).__init__()
        customer_id = request.view_args.values()[0]
        self.customer = Customer.retrieve(customer_id, self.group.id)
        if not self.customer:
            raise BillyExc['404_CUSTOMER_NOT_FOUND']

    @marshal_with(customer_view)
    def get(self, customer_id):
        """
        Retrieve a single customer
        """
        return self.customer

    @marshal_with(customer_view)
    def put(self, customer_id):
        """
        Update a customer, currently limited to updating their coupon.
        """
        customer_form = CustomerUpdateForm(request.form)
        if customer_form.validate():
            return customer_form.save(self.customer)
        else:
            self.form_error(customer_form.errors)
