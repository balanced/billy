from __future__ import unicode_literals

from utils.intervals import Intervals


def sample_payout(your_id='5_DOLLA_PLAN',
                  name='The 5 dollar Payout',
                  balance_to_keep_cents=500,
                  payout_interval=Intervals.WEEK):
    return dict(
        your_id=your_id,
        name=name,
        balance_to_keep_cents=balance_to_keep_cents,
        payout_interval=payout_interval
    )
