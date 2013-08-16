from __future__ import unicode_literals
import logging

from billy.models import tables
from billy.utils.generic import make_guid


class PlanModel(object):

    #: Daily frequency
    FREQ_DAILY = 0
    #: Weekly frequency
    FREQ_WEEKLY = 1
    #: Monthly frequency
    FREQ_MONTHLY = 2
    #: Annually frequency
    FREQ_YEARLY = 3

    FREQ_ALL = [
        FREQ_DAILY,
        FREQ_WEEKLY,
        FREQ_MONTHLY,
        FREQ_YEARLY,
    ]

    #: Charging type plan
    TYPE_CHARGE = 0
    #: Paying out type plan
    TYPE_PAYOUT = 1

    TYPE_ALL = [
        TYPE_CHARGE,
        TYPE_PAYOUT, 
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

    def create_plan(self, plan_type, amount, frequency, name=None):
        """Create a plan and return its ID

        """
        if plan_type not in self.TYPE_ALL:
            raise ValueError('Invalid plan_type {}'.format(plan_type))
        if frequency not in self.FREQ_ALL:
            raise ValueError('Invalid frequency {}'.format(frequency))
        plan = tables.Plan(
            guid='PL' + make_guid(),
            plan_type=plan_type,
            name=name, 
            amount=amount, 
            frequency=frequency, 
        )
        self.session.add(plan)
        self.session.flush()
        return plan.guid

    def update_plan(self, guid, **kwargs):
        """Update a plan

        """
        plan = self.get_plan_by_guid(guid, True)
        now = tables.now_func()
        plan.updated_at = now
        for key in ['name']:
            if key not in kwargs:
                continue
            value = kwargs.pop(key)
            setattr(plan, key, value)
        if kwargs:
            raise TypeError('Unknown attributes {} to update'.format(tuple(kwargs.keys())))
        self.session.add(plan)
        self.session.flush()
