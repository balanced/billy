from __future__ import unicode_literals


def sample_coupon(
        your_id='10_OFF_COUPON',
        name='First Invoice 10 off',
        price_off_cents=0,
        percent_off_int=10,
        max_redeem=-1,
        repeating=1):

    return dict(
        your_id=your_id,
        name=name,
        price_off_cents=price_off_cents,
        percent_off_int=percent_off_int,
        max_redeem=max_redeem,
        repeating=repeating
    )