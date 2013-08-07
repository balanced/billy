from __future__ import unicode_literals

from datetime import datetime

sample_customer = {
    'customer_id': 'MY_TEST_CUSTOMER',
    'provider_id': 'MY_DUMMY_PROVIDER'
}
sample_customer_2 = {
    'customer_id': 'MY_TEST_CUSTOMER_2',
    'provider_id': 'MY_DUMMY_PROVIDER_2'
}
sample_customer_3 = {
    'customer_id': 'MY_TEST_CUSTOMER_3',
    'provider_id': 'MY_DUMMY_PROVIDER_3'
}

sample_coupon = {
    'coupon_id': 'MY_TEST_COUPON',
    'name': 'Some Coupon',
    'price_off_cents': 1000,
    'percent_off_int': 0,
    'max_redeem': -1,
    'repeating': -1,
    'expire_at' : datetime(year=2014, month=5, day=1)
}