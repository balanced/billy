from __future__ import unicode_literals

from dateutil.relativedelta import relativedelta

from billy.models.plan import PlanModel


def next_transaction_datetime(started_at, frequency, period):
    """Get next transaction datetime from given frequency, started datetime
    and period

    :param started_at: the started datetime of the first transaction
    :param frequency: the plan frequency
    :param period: how many periods has been passed, 0 indicates this is the 
        very first transaction
    """
    if frequency not in PlanModel.FREQ_ALL:
        raise ValueError('Invalid frequency {}'.format(frequency))
    if period == 0:
        return started_at
    delta = None
    if frequency == PlanModel.FREQ_DAILY:
        delta = relativedelta(days=period)
    elif frequency == PlanModel.FREQ_WEEKLY:
        delta = relativedelta(weeks=period)
    elif frequency == PlanModel.FREQ_MONTHLY:
        delta = relativedelta(months=period)
    elif frequency == PlanModel.FREQ_YEARLY:
        delta = relativedelta(years=period)
    return started_at + delta
