from __future__ import unicode_literals

from flask import request
from flask.ext.restful import marshal_with

from billy.api.errors import BillyExc
from billy.api.resources.group import GroupController
from billy.models import ChargePlan
from .form import PlanCreateForm, PlanUpdateForm
from .view import plan_view


class PlanIndexController(GroupController):

    """
    Base ChargePlan resource used to create a plan or retrieve all your
    plans
    """

    @marshal_with(plan_view)
    def get(self):
        """
        Return a list of plans pertaining to a group
        """
        return self.group.plans.all()

    @marshal_with(plan_view)
    def post(self):
        """
        Create a plan
        """
        plan_form = PlanCreateForm(request.form)
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
        plan_id = request.view_args.values()[0]
        self.plan = ChargePlan.retrieve(plan_id, self.group.id)
        if not self.plan:
            raise BillyExc['404_PLAN_NOT_FOUND']

    @marshal_with(plan_view)
    def get(self, plan_id):
        """
        Retrieve a single plan
        """
        return self.plan

    @marshal_with(plan_view)
    def put(self, plan_id):
        """
        Update the name of a plan
        """
        plan_form = PlanUpdateForm(request.form)
        if plan_form.validate():
            return plan_form.save(self.plan)
        else:
            self.form_error(plan_form.errors)

    def delete(self, plan_id):
        """
        Deletes a plan by marking it inactive. Does not effect users already
        on the plan.
        """
        self.plan.delete()
        return None
