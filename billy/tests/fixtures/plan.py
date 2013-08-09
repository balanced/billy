from __future__ import unicode_literals

from utils.intervals import Intervals


def sample_plan(
        your_id='PRO_PLAN',
        name='The Pro Plan',
        price_cents=1000,
        plan_interval=Intervals.MONTH,
        trial_interval=Intervals.WEEK):
    return dict(
        your_id=your_id,
        name=name,
        price_cents=price_cents,
        plan_interval=plan_interval,
        trial_interval=trial_interval
    )
