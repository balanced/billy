from __future__ import unicode_literals

from flask import request
from flask.ext.restful import marshal_with

from api.errors import BillyExc
from api.resources.group import GroupController
from form import PayoutSubCreateForm, PayoutSubDeleteForm
from models import Customer, Company, PayoutSubscription
from view import payout_sub_view


class PayoutSubIndexController(GroupController):
    """
    Base PayoutSubscription resource used to create a payout subscription or
    retrieve all your payout subscriptions
    """

    @marshal_with(payout_sub_view)
    def get(self):
        """
        Return a list of payout subscriptions pertaining to a group
        """
        return PayoutSubscription.query.join(Customer).join(Company).filter(
            Company.guid == self.group.guid).all()

    @marshal_with(payout_sub_view)
    def post(self):
        """
        Create or update a payout subscription
        """
        sub_form = PayoutSubCreateForm(request.form)
        if sub_form.validate():
            return sub_form.save(self.group)
        else:
            self.form_error(sub_form.errors)

    @marshal_with(payout_sub_view)
    def delete(self):
        """
        Unsubscribe from the payout
        """
        sub_form = PayoutSubDeleteForm(request.form)
        if sub_form.validate():
            return sub_form.save(self.group)
        else:
            self.form_error(sub_form.errors)


class PayoutSubController(GroupController):
    """
    Methods pertaining to a single payout subscription
    """

    def __init__(self):
        super(PayoutSubController, self).__init__()
        payout_sub_id = request.view_args.values()[0]
        self.subscription = PayoutSubscription.query.filter(
            PayoutSubscription.guid == payout_sub_id).first()
        if not self.subscription:
            raise BillyExc['404_PAYOUT_SUB_NOT_FOUND']

    @marshal_with(payout_sub_view)
    def get(self, payout_sub_id):
        """
        Retrieve a single subscription
        """
        return self.subscription
