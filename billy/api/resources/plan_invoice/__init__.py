from __future__ import unicode_literals

from flask import request
from flask.ext.restful import marshal_with

from api.errors import BillyExc
from api.resources.group import GroupController
from models import Group, Customer, PlanInvoice, PlanSubscription
from view import plan_inv_view


class PlanInvIndexController(GroupController):
    """
    Base PlanInvoice resource used to create a plan invoice or
    retrieve all your plan invoices
    """

    @marshal_with(plan_inv_view)
    def get(self):
        """
        Return a list of plans invoices pertaining to a group
        """
        return PlanInvoice.query.join(PlanSubscription).join(Customer).join(
            Group).filter(Group.guid == self.group.guid).all()


class PlanInvController(GroupController):
    """
    Methods pertaining to a single plan invoice
    """

    def __init__(self):
        super(PlanInvController, self).__init__()
        plan_inv_id = request.view_args.values()[0]
        self.invoice = PlanInvoice.query.filter(
            PlanInvoice.guid == plan_inv_id).first()
        if not self.invoice:
            raise BillyExc['404_PLAN_INV_NOT_FOUND']

    @marshal_with(plan_inv_view)
    def get(self, plan_inv_id):
        """
        Retrieve a single invoice
        """
        return self.invoice
