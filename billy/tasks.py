from __future__ import unicode_literals

from billy.models import *

def main_task():
    Coupon.expire_coupons()
    PlanInvoice.clear_all_plan_debt()
    PlanInvoice.rollover_all()
    PayoutInvoice.make_all_payouts()
    PayoutInvoice.rollover_all()

if __name__ == "__main__":
    print "RUNNING TASK!"
    main_task()
