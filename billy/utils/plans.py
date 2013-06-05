from dateutil.relativedelta import relativedelta

class Intervals(object):
    """
    A class to represent and create relativedelta objects which will be used
    to define the plan intervals. Plan intervals MUST be defined using this class.
    """
    NONE = relativedelta(seconds=0)
    DAY = relativedelta(days=1)
    WEEK = relativedelta(weeks=1)
    TWO_WEEKS = relativedelta(weeks=2)
    MONTH = relativedelta(months=1)
    THREE_MONTHS = relativedelta(months=3)

    def custom(self, years=0, months=0, weeks=0, days=0, hours=0, minutes=0):
        """
        If one of the predefined intervals isn't useful you can create a custom
        plan interval with a resolution of upto a minute.
        """
        return relativedelta(years=years, months=months, weeks=weeks, days=days,
                             hours=hours, minutes=minutes)


