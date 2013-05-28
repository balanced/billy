from unittest import TestCase
from billy.plans import Intervals
from dateutil.relativedelta import relativedelta
class TestPlans(TestCase):

    def test_intervals(self):
        self.assertEqual(Intervals.DAY, relativedelta(days=1))
        self.assertEqual(Intervals.WEEK, relativedelta(weeks=1))
        self.assertEqual(Intervals.THREE_MONTHS, relativedelta(days=1))
        self.assertEqual(Intervals.DAY, relativedelta(days=1))
        self.assertEqual(Intervals.DAY, relativedelta(days=1))
