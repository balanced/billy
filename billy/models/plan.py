import logging

from billy.models import tables
from billy.utils.generic import make_guid


class PlanModel(object):

    FREQ_DAILY = 0
    FREQ_WEEKLY = 1
    FREQ_MONTHLY = 2
    FREQ_YEARLY = 3
    FREQ_ALL = [
        FREQ_DAILY,
        FREQ_WEEKLY,
        FREQ_MONTHLY,
        FREQ_YEARLY,
    ]

    def __init__(self, session, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.session = session

    def get_plan_by_guid(self, guid, raise_error=True):
        """Get a plan guid and return it

        :param guid: The guild of plan to get
        :param raise_error: Raise KeyError when cannot find one
        """
        query = self.session.query(tables.Plan).get(guid)
        return query

    def create_plan(self, name, amount, frequency, active=True):
        """Create a plan and return its ID

        """
        if frequency not in self.FREQ_ALL:
            raise ValueError('Invalid frequency %s' % frequency)
        plan = tables.Plan(
            guid=make_guid(),
            name=name, 
            amount=amount, 
            frequency=frequency, 
            active=active, 
        )
        self.session.add(plan)
        self.session.flush()
        return plan.guid

    def update_plan(self, guid, **kwargs):
        """Update a plan

        """
        plan = self.get_plan_by_guid(guid, True)
        if kwargs:
            now = tables.now_func()
            plan.updated_at = now
        for key in ['name', 'active']:
            if key not in kwargs:
                continue
            value = kwargs.pop(key)
            setattr(plan, key, value)
        if kwargs:
            raise TypeError('Unknown attributes {} to update'.format(tuple(kwargs.keys())))
        self.session.add(plan)
        self.session.flush()
