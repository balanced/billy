from __future__ import unicode_literals

from billy.models import tables
from billy.models.base import BaseTableModel
from billy.models.base import decorate_offset_limit
from billy.utils.generic import make_guid


class PlanModel(BaseTableModel):

    TABLE = tables.Plan

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

    @decorate_offset_limit
    def list_by_context(self, context):
        """List plan by a given context

        """
        Plan = tables.Plan
        query = (
            self.session
            .query(Plan)
            .filter(Plan.company == context)
            .order_by(tables.Plan.created_at.desc())
        )
        return query

    def create(
        self, 
        company, 
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
            company=company,
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
        return plan

    def update(self, plan, **kwargs):
        """Update a plan

        """
        now = tables.now_func()
        plan.updated_at = now
        for key in ['name', 'external_id', 'description']:
            if key not in kwargs:
                continue
            value = kwargs.pop(key)
            setattr(plan, key, value)
        if kwargs:
            raise TypeError('Unknown attributes {} to update'.format(tuple(kwargs.keys())))
        self.session.flush()

    def delete(self, plan):
        """Delete a plan

        """
        plan.deleted = True
        self.session.flush()
