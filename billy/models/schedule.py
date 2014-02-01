from __future__ import unicode_literals

from dateutil.relativedelta import relativedelta

from billy.models.plan import PlanModel


def next_transaction_datetime(started_at, frequency, period, interval=1):
    """Get next transaction datetime from given frequency, started datetime
    and period

    :param started_at: the started datetime of the first transaction
    :param frequency: the plan frequency
    :param period: how many periods has been passed, 0 indicates this is the
        first transaction
    :param interval: the interval of period, interval 3 with monthly
        frequency menas every 3 months
    """
    if interval < 1:
        raise ValueError('Interval can only be >= 1')
    if period == 0:
        return started_at
    delta = None
    if frequency == PlanModel.frequencies.DAILY:
        delta = relativedelta(days=period * interval)
    elif frequency == PlanModel.frequencies.WEEKLY:
        delta = relativedelta(weeks=period * interval)
    elif frequency == PlanModel.frequencies.MONTHLY:
        delta = relativedelta(months=period * interval)
    elif frequency == PlanModel.frequencies.YEARLY:
        delta = relativedelta(years=period * interval)
    return started_at + delta
