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

    def get(self, guid, raise_error=False, ignore_deleted=True):
        """Find a plan by guid and return it

        :param guid: The guild of plan to get
        :param raise_error: Raise KeyError when cannot find one
        """
        query = (
            self.session.query(tables.Plan)
            .filter_by(guid=guid)
            .filter_by(deleted=not ignore_deleted)
            .first()
        )
        if raise_error and query is None:
            raise KeyError('No such plan {}'.format(guid))
        return query

    def create(
        self, 
        company_guid, 
        plan_type, 
        amount, 
        frequency, 
        interval=1,
        external_id=None, 
        name=None, 
        description=None,
    ):
        """Create a plan and return its ID

        """
        if plan_type not in self.TYPE_ALL:
            raise ValueError('Invalid plan_type {}'.format(plan_type))
        if frequency not in self.FREQ_ALL:
            raise ValueError('Invalid frequency {}'.format(frequency))
        if interval < 1:
            raise ValueError('Interval can only be >= 1')
        now = tables.now_func()
        plan = tables.Plan(
            guid='PL' + make_guid(),
            company_guid=company_guid,
            plan_type=plan_type,
            amount=amount, 
            frequency=frequency, 
            interval=interval, 
            external_id=external_id, 
            name=name, 
            description=description,
            updated_at=now,
            created_at=now,
        )
        self.session.add(plan)
        self.session.flush()
        return plan.guid

    def update(self, guid, **kwargs):
        """Update a plan

        """
        plan = self.get(guid, raise_error=True)
        now = tables.now_func()
        plan.updated_at = now
        for key in ['name', 'external_id', 'description']:
            if key not in kwargs:
                continue
            value = kwargs.pop(key)
            setattr(plan, key, value)
        if kwargs:
            raise TypeError('Unknown attributes {} to update'.format(tuple(kwargs.keys())))
        self.session.add(plan)
        self.session.flush()

    def delete(self, guid):
        """Delete a plan

        """
        plan = self.get(guid, raise_error=True)
        plan.deleted = True
        self.session.add(plan)
        self.session.flush()
