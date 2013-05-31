from unittest import TestCase
from billy.plans.utils import Intervals
from billy.payout.utils import create_payout, list_payouts, update_payout, \
    retrieve_payout, delete_payout
from billy.errors import NotFoundError, BadIntervalError, AlreadyExistsError
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
from pytz import UTC
from billy.settings import query_tool
from billy.payout.models import Payout


class TestPayouts(TestCase):
    def setUp(self):
        self.marketplace = 'test_my_marketplace'
        query_tool.query(Payout).filter(Payout.marketplace == self
        .marketplace) \
            .delete()

    def test_intervals(self):
        self.assertEqual(Intervals.DAY, relativedelta(days=1))
        self.assertEqual(Intervals.WEEK, relativedelta(weeks=1))
        self.assertEqual(Intervals.THREE_MONTHS, relativedelta(months=3))
        self.assertEqual(Intervals.MONTH, relativedelta(months=1))
        self.assertEqual(Intervals.TWO_WEEKS, relativedelta(weeks=2))


    def test_create_and_retrieve(self):
        #Create the plan
        payout_id = 'test_my_payout_1'
        create_payout(payout_id, self.marketplace, 'Test Payout', 200,
                      Intervals.WEEK)
        #Retrieve the payout:
        result = retrieve_payout(payout_id, self.marketplace)
        self.assertEqual(result.payout_id, payout_id)
        self.assertEqual(result.marketplace, self.marketplace)
        self.assertEqual(result.name, 'Test Payout')
        self.assertEqual(result.payout_amount_cents, 200)
        self.assertLess(result.created_at - datetime.now(UTC),
                        timedelta(seconds=30))
        self.assertEqual(result.to_relativedelta(result.payout_interval),
                         Intervals.WEEK)
        #Try Creating duplicate
        self.assertRaises(AlreadyExistsError,
                          create_payout, payout_id, self.marketplace,
                          'Test Payout',
                          50, Intervals.MONTH, )
        #Create payout with bad payout_interval:
        self.assertRaises(BadIntervalError,
                          create_payout, 'test_my_payout_2', self.marketplace,
                          'Test Payout2', 1000, 'week')
        #Retrieve notexisting payout:
        self.assertRaises(NotFoundError, retrieve_payout, 'test_my_payout_DNE',
                          self.marketplace)


    def test_update_payout(self):
        payout_id = 'test_my_payout_3'
        payout_name = ('Test Payout', 'New payout name')
        create_payout(payout_id, self.marketplace, payout_name[0], 1000,
                      Intervals.WEEK)
        new_payout = retrieve_payout(payout_id, self.marketplace)
        self.assertEqual(new_payout.name, payout_name[0])
        update_payout(payout_id, self.marketplace, payout_name[1])
        changed_payout = retrieve_payout(payout_id, self.marketplace)
        self.assertEqual(changed_payout.name, payout_name[1])


    def test_delete_payout(self):
        payout_id = 'test_my_payout_4'
        marketplace = self.marketplace
        create_payout(payout_id, marketplace, 'Test', 1000, Intervals.TWO_WEEKS)
        current_payout = retrieve_payout(payout_id, marketplace)
        self.assertEqual(current_payout.active, True)
        delete_payout(payout_id, marketplace)
        deleted_payout = retrieve_payout(payout_id, self.marketplace)
        self.assertEqual(deleted_payout.active, False)
        self.assertLess(deleted_payout.deleted_at - datetime.now(UTC),
                        timedelta(seconds=30))
        self.assertRaises(NotFoundError, delete_payout, 'test_coupon_DNE',
                          self.marketplace)


    def test_list_payouts(self):
        create_payout('test_my_payout_5', self.marketplace, 'Test Payout 5',
                      5000,
                      Intervals.WEEK)
        create_payout('test_my_payout_6', self.marketplace, 'Test Payout 6',
                      5000, Intervals.WEEK)
        list_of_payouts = list_payouts(self.marketplace)
        self.assertEqual(len(list_of_payouts), 2)
        #Todo test active only

    def tearDown(self):
        query_tool.query(Payout).filter(Payout.marketplace == self.marketplace
        ).delete()
        query_tool.commit()
        self.assertFalse(list_payouts(self.marketplace))
        #TODO-me: Figure out why the last row isn't tearing down...SWITCH TO TRANSACTIONAL
