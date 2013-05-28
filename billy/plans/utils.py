from dateutil.relativedelta import relativedelta

class Intervals(object):
    DAY = relativedelta(days =1)
    WEEK = relativedelta(weeks=1)
    TWO_WEEKS = relativedelta(weeks=2)
    MONTH = relativedelta(months=1)
    THREE_MONTHS = relativedelta(months=3)

    def custom(self, years=0, months=0, weeks=0, days=0, hours=0, minutes=0):
        return relativedelta(years=years, months=months, weeks=weeks, days=days,
                             hours=hours, minutes=minutes)

