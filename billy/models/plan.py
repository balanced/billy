import logging

from billy.models import tables
from billy.utils.generic import make_guid


class PlanModel(object):

    def __init__(self, session, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.session = session

    def get_plan_by_guid(self, guid):
        """Get a plan guid and return it

        """
        query = self.session.query(tables.Plan).get(guid)
        return query

    def create_plan(self, name, amount):
        """Create a plan and return its ID

        """
        plan = tables.Plan(
            # TODO: generate GUID here
            guid=make_guid(),
            name=name, 
            amount=amount, 
        )
        self.session.add(plan)
        self.session.flush()
        return plan.guid
