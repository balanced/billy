from __future__ import unicode_literals

from models import Company
from tests import BaseTestCase
from tests.fixtures import (sample_company, sample_plan, sample_coupon,
                            sample_customer, sample_payout)


class ChargePlanInterfaceTest(BaseTestCase):
    def main_test(self):
        company = Company.create(**sample_company())

        # Create A Plan under the company
        plan = company.create_charge_plan(**sample_plan())


        #Create A Coupon under the company
        coupon = company.create_coupon(**sample_coupon())


        # Create A customer under the company:
        customer = company.create_customer(**sample_customer())


        # Subscribe Customer to a plan
        sub = plan.subscribe(customer, quantity=1, coupon=coupon)

        # Unsubscribe Customer from plan:
        sub.cancel()

        # Delete the test Company
        company.delete()


class ChargePayoutInterfaceTest(BaseTestCase):
    def main_test(self):
        company = Company.create(**sample_company())
        # Create A Payout under the company
        payout = company.create_payout_plan(**sample_payout())


        # Create A customer under the company:
        customer = company.create_customer(**sample_customer())

        # Subscribe Customer to a payout
        sub = payout.subscribe(customer)

        # Unsubscribe Customer from payout:
        sub.cancel()

        # Delete the test company
        company.delete()
