from __future__ import unicode_literals

from flask import request
from flask.ext.restful import marshal_with

from api.errors import BillyExc
from api.resources.group import GroupController
from models import Company, Customer, ChargeTransaction
from view import plan_trans_view


class PlanTransIndexController(GroupController):
    """
    Base ChargePlan Transaction resource used to create a plan transaction or
    retrieve all your plan transactions
    """

    @marshal_with(plan_trans_view)
    def get(self):
        """
        Return a list of plan transactions pertaining to a group
        """
        return ChargeTransaction.query.join(Customer).join(
            Company).filter(Company.id == self.group.id).all()


class PlanTransController(GroupController):
    """
    Methods pertaining to a single plan transaction
    """

    def __init__(self):
        super(PlanTransController, self).__init__()
        plan_trans_id = request.view_args.values()[0]
        self.trans = ChargeTransaction.query.filter(
            ChargeTransaction.id == plan_trans_id).first()
        if not self.trans:
            raise BillyExc['404_PLAN_TRANS_NOT_FOUND']

    @marshal_with(plan_trans_view)
    def get(self, plan_trans_id):
        """
        Retrieve a single transaction
        """
        return self.trans
