from __future__ import unicode_literals

from utils.intervals import Intervals

good_plan = dict(
    your_id='PRO_PLAN',
    name='The Pro Plan',
    price_cents=1000,  # 10 dollars
    plan_interval=Intervals.MONTH,  # Monthly plan
    trial_interval=Intervals.WEEK,
)
