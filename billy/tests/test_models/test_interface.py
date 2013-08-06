from __future__ import unicode_literals

from models import *
from utils.intervals import Intervals
from tests import BaseTestCase


class ChargePlanInterfaceTest(BaseTestCase):
    # CREATE A COMPANY

    def main_test(self):
        company = Company.create(
            processor_type='DUMMY',
            processor_api_key='MY_DUMMY_API_KEY',
            is_test=True,
        )

        # Create A Plan under the company
        plan = company.create_charge_plan(
            your_id='PRO_PLAN',
            name='The Pro Plan',
            price_cents=1000, # 10 dollars
            plan_interval=Intervals.MONTH, # Monthly plan
            trial_interval=Intervals.WEEK,
        )


        #Create A Coupon under the company
        coupon = company.add_coupon(
            your_id='10_OFF_COUPON',
            name='First Invoice 10 off',
            price_off_cents=0, # 0 dollars off
            percent_off_int=10, # 10 percent off
            max_redeem=-1, # Unlimited redemptions,
            repeating=1  # Only work on first invoice
        )


        # Create A customer under the company:
        customer = company.create_customer(
            your_id='customer_1215',
            # What you call your customer (usually id)
            # What your processor calls your customer
            provider_id='CUDEXKX1285DKE38DDK'
        )


        # Apply coupon to a customer
        coupon.redeem(customer)

        # Subscribe Customer to a plan
        invoice = plan.subscribe(customer, quantity=1)

        # Unsubscribe Customer from plan:
        plan.unsubscribe(customer)

        # Delete the test Company
        company.delete()


class ChargePayoutInterfaceTest(BaseTestCase):
    def main_test(self):
        company = Company.create(
            processor_type='DUMMY',
            processor_api_key='MY_DUMMY_API_KEY',
            is_test=True,
        )

        # Create A Payout under the company
        payout = company.create_payout_plan(
            your_id='5_DOLLA_PLAN',
            name='The 5 dollar Payout',
            balance_to_keep_cents=500, # Keep $5 in escrow
            payout_interval=Intervals.WEEK, # Weekly payout
        )


        # Create A customer under the company:
        customer = company.create_customer(
            your_id='customer_1215',
            # What you call your customer (usually id)
            provider_id='CUDEXKX1285DKE38DDK'
        )

        # Subscribe Customer to a payout
        invoice = payout.subscribe(customer)

        # Unsubscribe Customer from payout:
        payout.unsubscribe(customer)


        # Delete the test company
        company.delete()
