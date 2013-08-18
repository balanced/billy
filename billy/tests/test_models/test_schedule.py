from __future__ import unicode_literals
import unittest
import datetime

from freezegun import freeze_time


@freeze_time('2013-08-16')
class TestSchedule(unittest.TestCase):

    def assert_schedule(self, started_at, frequency, length, expected):
        from billy.models.schedule import next_transaction_datetime
        result = []
        for period in range(length):
            dt = next_transaction_datetime(started_at, frequency, period)
            result.append(dt)
        self.assertEqual(result, expected)

    def test_invalid_freq_type(self):
        from billy.models.schedule import next_transaction_datetime
        with self.assertRaises(ValueError):
            next_transaction_datetime(datetime.datetime.utcnow(), 999, 0)

    def test_daily_schedule(self):
        from billy.models.plan import PlanModel
        with freeze_time('2013-07-28'):
            now = datetime.datetime.utcnow()
            self.assert_schedule(now, PlanModel.FREQ_DAILY, 10, [
                datetime.datetime(2013, 7, 28),
                datetime.datetime(2013, 7, 29),
                datetime.datetime(2013, 7, 30),
                datetime.datetime(2013, 7, 31),
                datetime.datetime(2013, 8, 1),
                datetime.datetime(2013, 8, 2),
                datetime.datetime(2013, 8, 3),
                datetime.datetime(2013, 8, 4),
                datetime.datetime(2013, 8, 5),
                datetime.datetime(2013, 8, 6),
            ])

    def test_daily_schedule_with_end_of_month(self):
        from billy.models.plan import PlanModel
        from billy.models.schedule import next_transaction_datetime

        def assert_next_day(now_dt, expected):
            with freeze_time(now_dt):
                now = datetime.datetime.utcnow()
                next_dt = next_transaction_datetime(
                    started_at=now, 
                    frequency=PlanModel.FREQ_DAILY,
                    period=1, 
                )
                self.assertEqual(next_dt, expected)

        assert_next_day('2013-01-31', datetime.datetime(2013, 2, 1))
        assert_next_day('2013-02-28', datetime.datetime(2013, 3, 1))
        assert_next_day('2013-03-31', datetime.datetime(2013, 4, 1))
        assert_next_day('2013-04-30', datetime.datetime(2013, 5, 1))
        assert_next_day('2013-05-31', datetime.datetime(2013, 6, 1))
        assert_next_day('2013-06-30', datetime.datetime(2013, 7, 1))
        assert_next_day('2013-07-31', datetime.datetime(2013, 8, 1))
        assert_next_day('2013-08-31', datetime.datetime(2013, 9, 1))
        assert_next_day('2013-09-30', datetime.datetime(2013, 10, 1))
        assert_next_day('2013-10-31', datetime.datetime(2013, 11, 1))
        assert_next_day('2013-11-30', datetime.datetime(2013, 12, 1))
        assert_next_day('2013-12-31', datetime.datetime(2014, 1, 1))

    def test_weekly_schedule(self):
        from billy.models.plan import PlanModel
        with freeze_time('2013-08-18'):
            now = datetime.datetime.utcnow()
            self.assert_schedule(now, PlanModel.FREQ_WEEKLY, 5, [
                datetime.datetime(2013, 8, 18),
                datetime.datetime(2013, 8, 25),
                datetime.datetime(2013, 9, 1),
                datetime.datetime(2013, 9, 8),
                datetime.datetime(2013, 9, 15),
            ])

    def test_monthly_schedule(self):
        from billy.models.plan import PlanModel
        with freeze_time('2013-08-18'):
            now = datetime.datetime.utcnow()
            self.assert_schedule(now, PlanModel.FREQ_MONTHLY, 6, [
                datetime.datetime(2013, 8, 18),
                datetime.datetime(2013, 9, 18),
                datetime.datetime(2013, 10, 18),
                datetime.datetime(2013, 11, 18),
                datetime.datetime(2013, 12, 18),
                datetime.datetime(2014, 1, 18),
            ])

    def test_monthly_schedule_with_end_of_month(self):
        from billy.models.plan import PlanModel
        with freeze_time('2013-08-31'):
            now = datetime.datetime.utcnow()
            self.assert_schedule(now, PlanModel.FREQ_MONTHLY, 7, [
                datetime.datetime(2013, 8, 31),
                datetime.datetime(2013, 9, 30),
                datetime.datetime(2013, 10, 31),
                datetime.datetime(2013, 11, 30),
                datetime.datetime(2013, 12, 31),
                datetime.datetime(2014, 1, 31),
                datetime.datetime(2014, 2, 28),
            ])

        with freeze_time('2013-11-30'):
            now = datetime.datetime.utcnow()
            self.assert_schedule(now, PlanModel.FREQ_MONTHLY, 6, [
                datetime.datetime(2013, 11, 30),
                datetime.datetime(2013, 12, 30),
                datetime.datetime(2014, 1, 30),
                datetime.datetime(2014, 2, 28),
                datetime.datetime(2014, 3, 30),
                datetime.datetime(2014, 4, 30),
            ])

    def test_yearly_schedule(self):
        from billy.models.plan import PlanModel
        with freeze_time('2013-08-18'):
            now = datetime.datetime.utcnow()
            self.assert_schedule(now, PlanModel.FREQ_YEARLY, 5, [
                datetime.datetime(2013, 8, 18),
                datetime.datetime(2014, 8, 18),
                datetime.datetime(2015, 8, 18),
                datetime.datetime(2016, 8, 18),
                datetime.datetime(2017, 8, 18),
            ])

    def test_yearly_schedule_with_leap_year(self):
        from billy.models.plan import PlanModel
        with freeze_time('2012-02-29'):
            now = datetime.datetime.utcnow()
            self.assert_schedule(now, PlanModel.FREQ_YEARLY, 5, [
                datetime.datetime(2012, 2, 29),
                datetime.datetime(2013, 2, 28),
                datetime.datetime(2014, 2, 28),
                datetime.datetime(2015, 2, 28),
                datetime.datetime(2016, 2, 29),
            ])
