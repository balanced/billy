import logging

from billy.models import tables
from billy.utils.generic import make_guid


class PlanModel(object):

    FREQ_DAILY = 0
    FREQ_WEEKLY = 1
    FREQ_MONTHLY = 2
    FREQ_ALL = [
        FREQ_DAILY,
        FREQ_WEEKLY,
        FREQ_MONTHLY,
    ]

    def __init__(self, session, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.session = session

    def get_plan_by_guid(self, guid):
        """Get a plan guid and return it

        """
        query = self.session.query(tables.Plan).get(guid)
        return query

    def create_plan(self, name, amount, frequency):
        """Create a plan and return its ID

        """
        if frequency not in self.FREQ_ALL:
            raise ValueError('Invalid frequency %s' % frequency)
        plan = tables.Plan(
            guid=make_guid(),
            name=name, 
            amount=amount, 
            frequency=frequency, 
        )
        self.session.add(plan)
        self.session.flush()
        return plan.guid
