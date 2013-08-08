from __future__ import unicode_literals

from utils.intervals import Intervals

good_payout = dict(
    your_id='5_DOLLA_PLAN',
    name='The 5 dollar Payout',
    balance_to_keep_cents=500, # Keep $5 in escrow
    payout_interval=Intervals.WEEK, # Weekly payout
)
