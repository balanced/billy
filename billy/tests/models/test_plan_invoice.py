from __future__ import unicode_literals
from datetime import datetime

from freezegun import freeze_time
from pytz import UTC
from sqlalchemy.exc import *
from sqlalchemy.orm.exc import *

from billy.models import Group, Customer, Plan, PlanInvoice
from billy.utils.intervals import Intervals
from billy.tests import BalancedTransactionalTestCase

class TestPlanInvoice(BalancedTransactionalTestCase):

    def setUp(self):
        super(TestPlanInvoice, self).setUp()
        self.customer = 'MY_TEST_CUSTOMER'
        self.customer_2 = 'MY_TEST_CUSTOMER_2'
        self.customer_group2 = 'MY_TEST_CUSTOMER_3'
        self.group = 'BILLY_TEST_MARKETPLACE'
        self.group_2 = 'BILLY_TEST_MARKETPLACE_2'
        self.plan_id = 'MY_TEST_PLAN'
        self.plan_id_2 = 'MY_TEST_PLAN_2'
        self.now = datetime.now(UTC)
        self.week = self.now + Intervals.WEEK
        self.two_weeks = self.now + Intervals.WEEK
        self.month = self.now + Intervals.MONTH
        Group.create_group(self.group)
        Group.create_group(self.group_2)
        Customer.create(self.customer, self.group)
        Customer.create(self.customer_2, self.group)
        Customer.create(self.customer_group2, self.group_2)
        Plan.create(
            external_id=self.plan_id,
            group_id=self.group,
            name='Starter',
            price_cents=1000,
            plan_interval=Intervals.MONTH,
            trial_interval=Intervals.WEEK
        )
        Plan.create(
            external_id=self.plan_id_2,
            group_id=self.group,
            name='Starter',
            price_cents=15000,
            plan_interval=Intervals.MONTH,
            trial_interval=Intervals.WEEK
        )






class TestCreate(TestPlanInvoice):

    def test_create(self):
        PlanInvoice.create(
            customer_id=self.customer,
            group_id=self.group,
            relevant_plan=self.plan_id,
            relevant_coupon=None,
            start_dt=self.now,
            end_dt=self.month,
            due_dt=self.week,
            amount_base_cents=1000,
            amount_after_coupon_cents=1000,
            amount_paid_cents=1000,
            remaining_balance_cents=1000,
            quantity=10,
            charge_at_period_end=False,
            includes_trial=False,
        )


    def test_create_exists(self):
        PlanInvoice.create(
            customer_id=self.customer,
            group_id=self.group,
            relevant_plan=self.plan_id,
            relevant_coupon=None,
            start_dt=self.now,
            end_dt=self.month,
            due_dt=self.week,
            amount_base_cents=1000,
            amount_after_coupon_cents=1000,
            amount_paid_cents=1000,
            remaining_balance_cents=1000,
            quantity=10,
            charge_at_period_end=False,
            includes_trial=False,
                        )
        with self.assertRaises(IntegrityError):
            PlanInvoice.create(
                customer_id=self.customer,
                group_id=self.group,
                relevant_plan=self.plan_id,
                relevant_coupon=None,
                start_dt=self.now,
                end_dt=self.month,
                due_dt=self.week,
                amount_base_cents=1000,
                amount_after_coupon_cents=1000,
                amount_paid_cents=1000,
                remaining_balance_cents=1000,
                quantity=10,
                charge_at_period_end=False,
                includes_trial=False,
                )



    def test_create_customer_dne(self):
        with self.assertRaises(IntegrityError):
            PlanInvoice.create(
                customer_id='CUST_DNE',
                group_id=self.group,
                relevant_plan=self.plan_id,
                relevant_coupon=None,
                start_dt=self.now,
                end_dt=self.month,
                due_dt=self.week,
                amount_base_cents=1000,
                amount_after_coupon_cents=1000,
                amount_paid_cents=1000,
                remaining_balance_cents=1000,
                quantity=10,
                charge_at_period_end=False,
                includes_trial=False,
                )

    def test_create_exist_inactive(self):
        var = PlanInvoice.create(
            customer_id=self.customer,
            group_id=self.group,
            relevant_plan=self.plan_id,
            relevant_coupon=None,
            start_dt=self.now,
            end_dt=self.month,
            due_dt=self.week,
            amount_base_cents=1000,
            amount_after_coupon_cents=1000,
            amount_paid_cents=1000,
            remaining_balance_cents=1000,
            quantity=10,
            charge_at_period_end=False,
            includes_trial=False,
        )
        var.active = False
        var.session.flush()
        PlanInvoice.create(
            customer_id=self.customer,
            group_id=self.group,
            relevant_plan=self.plan_id,
            relevant_coupon=None,
            start_dt=self.now,
            end_dt=self.month,
            due_dt=self.week,
            amount_base_cents=1000,
            amount_after_coupon_cents=1000,
            amount_paid_cents=1000,
            remaining_balance_cents=1000,
            quantity=10,
            charge_at_period_end=False,
            includes_trial=False,
            )




class TestRetrieve(TestPlanInvoice):

    def test_create_and_retrieve(self):
        PlanInvoice.create(
            customer_id=self.customer,
            group_id=self.group,
            relevant_plan=self.plan_id,
            relevant_coupon=None,
            start_dt=self.now,
            end_dt=self.month,
            due_dt=self.week,
            amount_base_cents=1000,
            amount_after_coupon_cents=1000,
            amount_paid_cents=1000,
            remaining_balance_cents=1000,
            quantity=10,
            charge_at_period_end=False,
            includes_trial=False,
            )
        res = PlanInvoice.retrieve(self.customer,self.group, self.plan_id, active_only=True)
        self.assertEqual(res.amount_base_cents, 1000)



    def test_retrieve_dne(self):
        with self.assertRaises(NoResultFound):
            PlanInvoice.retrieve('CUSTOMER_DNE', self.group, self.plan_id, active_only=True)


    def test_retrieve_params(self):
        PlanInvoice.create(
            customer_id=self.customer,
            group_id=self.group,
            relevant_plan=self.plan_id,
            relevant_coupon=None,
            start_dt=self.now,
            end_dt=self.month,
            due_dt=self.week,
            amount_base_cents=1000,
            amount_after_coupon_cents=800,
            amount_paid_cents=200,
            remaining_balance_cents=600,
            quantity=10,
            charge_at_period_end=False,
            includes_trial=False,
            )
        res = PlanInvoice.retrieve(self.customer, self.group, self.plan_id, active_only=True)
        self.assertEqual(res.customer_id, self.customer)
        self.assertTrue(res.active)
        self.assertEqual(res.relevant_plan, self.plan_id)
        self.assertEqual(res.relevant_coupon, None)
        self.assertEqual(res.start_dt, self.now)
        self.assertEqual(res.due_dt, self.week)
        self.assertEqual(res.end_dt, self.month)
        self.assertEqual(res.amount_base_cents, 1000)
        self.assertEqual(res.amount_after_coupon_cents, 800)
        self.assertEqual(res.amount_paid_cents, 200)
        self.assertEqual(res.remaining_balance_cents, 600)
        self.assertEqual(res.quantity, 10)
        self.assertFalse(res.charge_at_period_end)
        self.assertFalse(res.includes_trial)

    def test_retrieve_active_only(self):
        ret = PlanInvoice.create(
            customer_id=self.customer,
            group_id=self.group,
            relevant_plan=self.plan_id,
            relevant_coupon=None,
            start_dt=self.now,
            end_dt=self.month,
            due_dt=self.week,
            amount_base_cents=1000,
            amount_after_coupon_cents=800,
            amount_paid_cents=200,
            remaining_balance_cents=600,
            quantity=10,
            charge_at_period_end=False,
            includes_trial=False,
            )
        ret.active = False
        ret.session.commit()
        with self.assertRaises(NoResultFound):
            PlanInvoice.retrieve(self.customer, self.group, self.plan_id, active_only=True)


    def test_list(self):
        PlanInvoice.create(
            customer_id=self.customer,
            group_id=self.group,
            relevant_plan=self.plan_id,
            relevant_coupon=None,
            start_dt=self.now,
            end_dt=self.month,
            due_dt=self.week,
            amount_base_cents=2000,
            amount_after_coupon_cents=800,
            amount_paid_cents=200,
            remaining_balance_cents=600,
            quantity=10,
            charge_at_period_end=False,
            includes_trial=False,
            )
        PlanInvoice.create(
            customer_id=self.customer_2,
            group_id=self.group,
            relevant_plan=self.plan_id,
            relevant_coupon=None,
            start_dt=self.now,
            end_dt=self.month,
            due_dt=self.week,
            amount_base_cents=1000,
            amount_after_coupon_cents=800,
            amount_paid_cents=200,
            remaining_balance_cents=600,
            quantity=10,
            charge_at_period_end=False,
            includes_trial=False,
            )
        list = PlanInvoice.list(self.group)
        self.assertEqual(len(list), 2)


    def test_list_active_only(self):
        PlanInvoice.create(
            customer_id=self.customer,
            group_id=self.group,
            relevant_plan=self.plan_id,
            relevant_coupon=None,
            start_dt=self.now,
            end_dt=self.month,
            due_dt=self.week,
            amount_base_cents=2000,
            amount_after_coupon_cents=800,
            amount_paid_cents=200,
            remaining_balance_cents=600,
            quantity=10,
            charge_at_period_end=False,
            includes_trial=False,
            )
        two = PlanInvoice.create(
            customer_id=self.customer_2,
            group_id=self.group,
            relevant_plan=self.plan_id,
            relevant_coupon=None,
            start_dt=self.now,
            end_dt=self.month,
            due_dt=self.week,
            amount_base_cents=1000,
            amount_after_coupon_cents=800,
            amount_paid_cents=200,
            remaining_balance_cents=600,
            quantity=10,
            charge_at_period_end=False,
            includes_trial=False,
            )
        two.active = False
        two.session.commit()
        list = PlanInvoice.list(self.group, active_only=True)
        self.assertEqual(len(list), 1)



class TestUtils(TestPlanInvoice):

    def setUp(self):
        super(TestUtils, self).setUp()
        PlanInvoice.create(
            customer_id=self.customer,
            group_id=self.group,
            relevant_plan=self.plan_id,
            relevant_coupon=None,
            start_dt=self.now,
            end_dt=self.month,
            due_dt=self.week,
            amount_base_cents=2000,
            amount_after_coupon_cents=800,
            amount_paid_cents=200,
            remaining_balance_cents=600,
            quantity=10,
            charge_at_period_end=False,
            includes_trial=False,
            )
        PlanInvoice.create(
            customer_id=self.customer,
            group_id=self.group,
            relevant_plan=self.plan_id_2,
            relevant_coupon=None,
            start_dt=self.now,
            end_dt=self.month,
            due_dt=self.week,
            amount_base_cents=2000,
            amount_after_coupon_cents=800,
            amount_paid_cents=200,
            remaining_balance_cents=600,
            quantity=10,
            charge_at_period_end=False,
            includes_trial=False,
            )
        PlanInvoice.create(
            customer_id=self.customer_2,
            group_id=self.group,
            relevant_plan=self.plan_id,
            relevant_coupon=None,
            start_dt=self.now,
            end_dt=self.month,
            due_dt=self.month,
            amount_base_cents=1000,
            amount_after_coupon_cents=800,
            amount_paid_cents=200,
            remaining_balance_cents=600,
            quantity=10,
            charge_at_period_end=False,
            includes_trial=False,
            )


    def test_needs_rollover(self):
        with freeze_time(str(self.month)):
            list = PlanInvoice.needs_plan_debt_cleared()
            for each in list:
                each.clear_plan_debt()
            list = PlanInvoice.need_rollover()
            self.assertEqual(len(list), 3)



    def test_rollover(self):
        with freeze_time(str(self.month)):
            list = PlanInvoice.needs_plan_debt_cleared()
            for each in list:
                each.clear_plan_debt()
            invoices = PlanInvoice.need_rollover()
            for invoice in invoices:
                invoice.rollover()


    def test_rollover_all(self):
        with freeze_time(str(self.month + Intervals.TWO_WEEKS)):
            PlanInvoice.clear_all_plan_debt()
            count_invoices = PlanInvoice.rollover_all()
            self.assertEqual(count_invoices, 3)

    def test_needs_debt_cleared(self):
        list = PlanInvoice.needs_plan_debt_cleared()
        self.assertEqual(len(list), 0)
        with freeze_time(str(self.two_weeks)):
            list = PlanInvoice.needs_plan_debt_cleared()
            self.assertEqual(len(list), 1)
        with freeze_time(str(self.month)):
            list = PlanInvoice.needs_plan_debt_cleared()
            self.assertEqual(len(list), 2)

    def test_clear_all_plan_debt(self):
        with freeze_time(str(self.month)):
            PlanInvoice.clear_all_plan_debt()
            self.assertEqual(len(PlanInvoice.needs_plan_debt_cleared()), 0)



class TestValidators(TestPlanInvoice):

    def test_amount_base_cents(self):
        with self.assertRaises(ValueError):
            PlanInvoice.create(
                customer_id=self.customer,
                group_id=self.group,
                relevant_plan=self.plan_id,
                relevant_coupon=None,
                start_dt=self.now,
                end_dt=self.month,
                due_dt=self.week,
                amount_base_cents=-1000,
                amount_after_coupon_cents=1000,
                amount_paid_cents=1000,
                remaining_balance_cents=1000,
                quantity=10,
                charge_at_period_end=False,
                includes_trial=False,
                )

    def test_amount_after_coupon_cents(self):
        with self.assertRaises(ValueError):
            PlanInvoice.create(
                customer_id=self.customer,
                group_id=self.group,
                relevant_plan=self.plan_id,
                relevant_coupon=None,
                start_dt=self.now,
                end_dt=self.month,
                due_dt=self.week,
                amount_base_cents=1000,
                amount_after_coupon_cents=-1000,
                amount_paid_cents=1000,
                remaining_balance_cents=1000,
                quantity=10,
                charge_at_period_end=False,
                includes_trial=False,
                )

    def test_amount_paid_cents(self):
        with self.assertRaises(ValueError):
            PlanInvoice.create(
                customer_id=self.customer,
                group_id=self.group,
                relevant_plan=self.plan_id,
                relevant_coupon=None,
                start_dt=self.now,
                end_dt=self.month,
                due_dt=self.week,
                amount_base_cents=1000,
                amount_after_coupon_cents=1000,
                amount_paid_cents=-1000,
                remaining_balance_cents=1000,
                quantity=10,
                charge_at_period_end=False,
                includes_trial=False,
                )

    def test_quantity(self):
        with self.assertRaises(ValueError):
            PlanInvoice.create(
                customer_id=self.customer,
                group_id=self.group,
                relevant_plan=self.plan_id,
                relevant_coupon=None,
                start_dt=self.now,
                end_dt=self.month,
                due_dt=self.week,
                amount_base_cents=1000,
                amount_after_coupon_cents=1000,
                amount_paid_cents=1000,
                remaining_balance_cents=1000,
                quantity=-10,
                charge_at_period_end=False,
                includes_trial=False,
                )









