from __future__ import unicode_literals

from flask import request
from flask.ext.restful import marshal_with

from api.errors import BillyExc
from api.resources.group import GroupController
from form import PlanSubCreateForm, PlanSubDeleteForm
from models import Group, PlanSubscription
from view import plan_sub_view


class PlanSubIndexController(GroupController):

    """
    Base PlanSubscription resource used to create a plan subscription or
    retrieve all your plan subscriptions
    """

    @marshal_with(plan_sub_view)
    def get(self):
        """
        Return a list of plans subscriptions pertaining to a group
        """
        return PlanSubscription.query.filter(Group.guid == self.group.guid)

    @marshal_with(plan_sub_view)
    def post(self):
        """
        Create or update a plan subscription
        """
        sub_form = PlanSubCreateForm(request.form)
        if sub_form.validate():
            return sub_form.save(self.group)
        else:
            self.form_error(sub_form.errors)

    @marshal_with(plan_sub_view)
    def delete(self):
        """
        Unsubscribe from the plan
        """
        plan_form = PlanSubDeleteForm(request.form)
        if plan_form.validate():
            return plan_form.save(self.group)
        else:
            self.form_error(plan_form.errors)


class PlanController(GroupController):

    """
    Methods pertaining to a single plan
    """

    def __init__(self):
        super(PlanController, self).__init__()
        plan_sub_id = request.view_args.values()[0]
        self.subscription = PlanSubscription.filter(PlanSubscription.guid == plan_sub_id).frist()
        if not self.subscription:
            raise BillyExc['404_PLAN_NOT_FOUND']

    @marshal_with(plan_sub_view)
    def get(self, plan_sub_id):
        """
        Retrieve a single subscription
        """
        return self.subscription