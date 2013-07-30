from __future__ import unicode_literals

from dateutil.relativedelta import relativedelta
from flask.ext.restful import fields
import json
from wtforms import Field, TextField


class Intervals(object):

    """
    A class to represent and create relativedelta objects which will be used
    to define the plan intervals. Plan intervals MUST be defined using this
    class.
    """
    NONE = relativedelta(seconds=0)
    TWELVE_HOURS = relativedelta(hours=12)
    DAY = relativedelta(days=1)
    THREE_DAYS = relativedelta(days=3)
    WEEK = relativedelta(weeks=1)
    TWO_WEEKS = relativedelta(weeks=2)
    THREE_WEEKS = relativedelta(weeks=3)
    MONTH = relativedelta(months=1)
    TWO_MONTHS = relativedelta(months=2)
    THREE_MONTHS = relativedelta(months=3)
    SIX_MONTHS = relativedelta(months=6)
    NINE_MONTHS = relativedelta(months=9)
    YEAR = relativedelta(years=1)

    @classmethod
    def custom(cls, years=0, months=0, weeks=0, days=0, hours=0):
        """
        If one of the predefined intervals isn't useful you can create a custom
        plan interval with a resolution of up to a minute.
        """
        return relativedelta(
            years=years, months=months, weeks=weeks, days=days,
            hours=hours)


def interval_matcher(string):
    """
    This method takes a string and converts it to a interval object.
    Functioning examples:
    week two_weeks month three_months or a json with params:
    years, months, weeks, days, hours
    """
    if hasattr(Intervals, string.upper()):
        return getattr(Intervals, string.upper())
    else:
        try:
            data = json.loads(string)
            relativedelta(
                years=int(data.get('years', 0)),
                months=int(data.get('months', 0)),
                weeks=int(data.get('weeks', 0)),
                days=int(data.get('days', 0)),
                hours=int(data.get('hours', 0)),
            )
        except (ValueError, TypeError):
            raise ValueError


class IntervalViewField(fields.Raw):

    def format(self, inter):
        return {
            'years': inter.years,
            'months': inter.months,
            'days': inter.days,
            'hours': inter.hours,
        }
