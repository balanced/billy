from __future__ import unicode_literals

from models import Company
from tests import BaseTestCase
from tests.fixtures import (good_company, good_plan, good_coupon, good_customer,
                            good_payout)


class ChargePlanInterfaceTest(BaseTestCase):
    # CREATE A COMPANY

    def main_test(self):
        company = Company.create(**good_company)

        # Create A Plan under the company
        plan = company.create_charge_plan(**good_plan)


        #Create A Coupon under the company
        coupon = company.create_coupon(**good_coupon)


        # Create A customer under the company:
        customer = company.create_customer(**good_customer)


        # Subscribe Customer to a plan
        sub = plan.subscribe(customer, quantity=1, coupon=coupon)

        # Unsubscribe Customer from plan:
        sub.cancel()

        # Delete the test Company
        company.delete()


class ChargePayoutInterfaceTest(BaseTestCase):
    def main_test(self):
        company = Company.create(**good_company)
        # Create A Payout under the company
        payout = company.create_payout_plan(**good_payout)


        # Create A customer under the company:
        customer = company.create_customer(**good_customer)

        # Subscribe Customer to a payout
        sub = payout.subscribe(customer)

        # Unsubscribe Customer from payout:
        sub.cancel()


        # Delete the test company
        company.delete()
