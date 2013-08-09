from __future__ import unicode_literals
from datetime import datetime

from freezegun import freeze_time

from models import Company
from utils.intervals import Intervals
from tests.fixtures import sample_coupon, sample_company, sample_customer, sample_plan
from tests import BaseTestCase


class PlanScenarioTest(BaseTestCase):
    def main_test(self):
        # Lets go to the future
        with freeze_time('2014-01-01'):
            # Create a dummy test company
            company = Company.create(**sample_company())

            # Create a plan under the company
            plan = company.create_charge_plan(**sample_plan())

            # Create a customer under the company
            customer = company.create_customer(**sample_customer())

            # Create a coupon under the company
            coupon = company.create_coupon(**sample_coupon())

            # Subscribe the customer to the plan using that coupon
            sub = plan.subscribe(customer, quantity=1, coupon=coupon)

            # Subscription will now renew and the person is enrolled
            self.assertTrue(sub.is_enrolled)
            self.assertTrue(sub.should_renew)
            # An invoice is generated for that user
            invoice = sub.current_invoice

            # 10% off coupon:
            self.assertEqual(invoice.remaining_balance_cents, 900)

            # None of its paid yet:
            self.assertEqual(invoice.amount_paid_cents, 0)

            # Invoice should start now:
            self.assertEqual(invoice.start_dt, datetime.utcnow())

            # But it should be due in a week because of the trial
            self.assertTrue(invoice.includes_trial)
            self.assertEqual(invoice.due_dt, datetime.utcnow() + Intervals.WEEK)

