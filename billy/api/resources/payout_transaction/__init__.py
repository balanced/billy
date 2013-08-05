from __future__ import unicode_literals

from flask import request
from flask.ext.restful import marshal_with

from api.errors import BillyExc
from api.resources.group import GroupController
from models import Company, Customer, PayoutTransaction
from view import payout_trans_view


class PayoutTransIndexController(GroupController):
    """
    Base PayoutPlan Transaction resource used to create a payout transaction or
    retrieve all your payout transactions
    """

    @marshal_with(payout_trans_view)
    def get(self):
        """
        Return a list of payout transactions pertaining to a group
        """
        return PayoutTransaction.query.join(Customer).join(
            Company).filter(Company.guid == self.group.guid).all()


class PayoutTransController(GroupController):
    """
    Methods pertaining to a single payout transaction
    """

    def __init__(self):
        super(PayoutTransController, self).__init__()
        payout_trans_id = request.view_args.values()[0]
        self.trans = PayoutTransaction.query.filter(
            PayoutTransaction.guid == payout_trans_id).first()
        if not self.trans:
            raise BillyExc['404_PAYOUT_TRANS_NOT_FOUND']

    @marshal_with(payout_trans_view)
    def get(self, payout_trans_id):
        """
        Retrieve a single transaction
        """
        return self.trans
