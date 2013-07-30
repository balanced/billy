from __future__ import unicode_literals

from flask import request
from flask.ext.restful import marshal_with

from api.errors import BillyExc
from api.resources.group import GroupController
from models import Payout
from form import PayoutCreateForm, PayoutUpdateForm
from view import payout_view


class PayoutIndexController(GroupController):
    """
    Base Payout resource used to create a payout or retrieve all your
    payouts
    """

    @marshal_with(payout_view)
    def get(self):
        """
        Return a list of payouts pertaining to a group
        """
        return self.group.payouts.all()

    @marshal_with(payout_view)
    def post(self):
        """
        Create a payout
        """
        payout_form = PayoutCreateForm(request.form)
        if payout_form.validate():
            return payout_form.save(self.group)
        else:
            self.form_error(payout_form.errors)


class PayoutController(GroupController):
    """
    Methods pertaining to a single payout
    """

    def __init__(self):
        super(PayoutController, self).__init__()
        payout_id = request.view_args.values()[0]
        self.payout = Payout.retrieve(payout_id, self.group.guid)
        if not self.payout:
            raise BillyExc['404_PAYOUT_NOT_FOUND']

    @marshal_with(payout_view)
    def get(self, payout_id):
        """
        Retrieve a single payout
        """
        return self.payout


    @marshal_with(payout_view)
    def put(self, payout_id):
        """
        Update the name of a payout
        """
        payout_form = PayoutUpdateForm(request.form)
        if payout_form.validate():
            return payout_form.save(self.payout)
        else:
            self.form_error(payout_form.errors)

    def delete(self, payout_id):
        """
        Deletes a payout by marking it inactive. Does not effect users already
        on the payout.
        """
        self.payout.delete()
        return None



