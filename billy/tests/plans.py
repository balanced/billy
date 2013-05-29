from unittest import TestCase
from billy.plans.utils import Intervals, create_plan, delete_plan, list_plans, update_plan, retrieve_plan
from billy.errors import NotFoundError, BadIntervalError, AlreadyExistsError
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
from pytz import UTC
from billy.settings import query_tool
from billy.plans.models import Plan

class TestPlans(TestCase):
    
    def setUp(self):
        self.marketplace = 'test_my_marketplace'
        query_tool.query(Plan).filter(Plan.marketplace == self.marketplace).delete()
    
    def test_intervals(self):
        self.assertEqual(Intervals.DAY, relativedelta(days=1))
        self.assertEqual(Intervals.WEEK, relativedelta(weeks=1))
        self.assertEqual(Intervals.THREE_MONTHS, relativedelta(months=3))
        self.assertEqual(Intervals.MONTH, relativedelta(months=1))
        self.assertEqual(Intervals.TWO_WEEKS, relativedelta(weeks=2))


    def test_create_and_retrieve(self):
        #Create the plan
        plan_id = 'test_my_plan_1'
        new_plan = create_plan(plan_id, self.marketplace, 'Test Plan', 1000,
                               Intervals.WEEK, Intervals.DAY)
        #Retrieve the plan:
        result = retrieve_plan(plan_id, self.marketplace)
        self.assertEqual(result.plan_id, plan_id)
        self.assertEqual(result.marketplace, self.marketplace)
        self.assertEqual(result.name, 'Test Plan')
        self.assertEqual(result.price_cents, 1000)
        self.assertLess(result.created_at - datetime.now(UTC), timedelta(seconds=30))
        self.assertEqual(result.to_relativedelta(result.plan_interval), Intervals.WEEK)
        self.assertEqual(result.to_relativedelta(result.trial_interval), Intervals.DAY)
        #Try Creating duplicate
        self.assertRaises(AlreadyExistsError,
            create_plan ,plan_id, self.marketplace, 'Test Plan', 50,
                                  Intervals.MONTH, Intervals.WEEK)
        #Create plan with bad plan_interval:
        self.assertRaises(BadIntervalError,
                          create_plan,'test_my_plan_2', self.marketplace, 'Test Plan2', 1000, 'week',
                                      Intervals.DAY)
        #Retrieve notexisting plan:
        self.assertRaises(NotFoundError, retrieve_plan,'test_my_plan_DNE', self.marketplace)


    def test_update_plan(self):
         plan_id = 'test_my_plan_3'
         plan_name_orig = 'Test Plan'
         plan_name_new = 'New plan name'
         create_plan(plan_id, self.marketplace, plan_name_orig, 1000,
                               Intervals.WEEK, Intervals.DAY)
         new_plan = retrieve_plan(plan_id, self.marketplace)
         self.assertEqual(new_plan.name, plan_name_orig)
         update_plan(plan_id, self.marketplace, plan_name_new)
         changed_plan = retrieve_plan(plan_id, self.marketplace)
         self.assertEqual(changed_plan.name, plan_name_new)


    def test_delete_plan(self):
        plan_id = 'test_my_plan_4'
        marketplace = self.marketplace
        create_plan(plan_id, marketplace, 'Test', 1000, Intervals.TWO_WEEKS, Intervals.DAY)
        current_plan = retrieve_plan(plan_id, marketplace)
        self.assertEqual(current_plan.active, True)
        delete_plan(plan_id, marketplace)
        deleted_plan = retrieve_plan(plan_id, self.marketplace)
        self.assertEqual(deleted_plan.active, False)
        self.assertLess(deleted_plan.deleted_at - datetime.now(UTC), timedelta(seconds=30))
        self.assertRaises(NotFoundError, delete_plan, 'test_my_plan_5', self.marketplace)


    def test_list_plans(self):
        create_plan('test_my_plan_6', self.marketplace, 'Test Plan 6', 5000,
                    Intervals.WEEK, Intervals.DAY)
        create_plan('test_my_plan_7', self.marketplace, 'Test Plan 7', 5000,
                    Intervals.WEEK, Intervals.DAY)
        list_of_plans = list_plans(self.marketplace)
        self.assertGreater(len(list_of_plans), 1)


    def tearDown(self):
        query_tool.query(Plan).filter(Plan.marketplace == self.marketplace).delete()
        self.assertFalse(list_plans(self.marketplace))
        #TODO-me: Figure out why the last row isn't tearing down...SWITCH TO TRANSACTIONAL
