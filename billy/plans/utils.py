from dateutil.relativedelta import relativedelta
from models import Plan
from billy.settings import query_tool
from pytz import UTC
from datetime import datetime


class Intervals(object):
    """
    A class to represent and create relativedelta objects which will be used
    to define the plan intervals. Plan intervals MUST be defined using this class.
    """
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


def create_plan(plan_id, marketplace, name, price_cents, plan_interval, trial_interval):
    """
    Creates a plan that users can be assigned to.
    :param plan_id: A unique id/uri for the plan
    :param marketplace: a group/marketplace id/uri the user should be placed in (matches balanced payments marketplaces)
    :param name: A display name for the plan
    :param price_cents: Price in cents of the plan per interval. $1.00 = 100
    :param plan_interval: A Interval class that defines how frequently the charge the plan
    :param trial_interval: A Interval class that defines how long the initial trial is
    :return: True if success or raises error if not
    :raise: ValueError if plan doesn't exists, TypeError if intervals are not relativedelta (Interval class)
    """
    exists = query_tool(Plan).filter(Plan.plan_id == plan_id, Plan.marketplace == marketplace)
    if not exists:
        new_plan = Plan(id, marketplace, name, price_cents, plan_interval, trial_interval)
        query_tool.add(new_plan)
        query_tool.commit()
        return True
    else:
        raise ValueError('Plan already exists. Use different id')


def update_plan(plan_id, marketplace, new_name):
    """
    Updates ONLY the plan name. By design the only updateable field is the name.
    To change other params create a new plan.
    :param plan_id: The plan id/uri
    :param marketplace: The group/marketplace id/uri
    :param new_name: The new display name for the plan
    """
    exists = query_tool(Plan).filter(Plan.plan_id == plan_id).first()
    if not exists:
        raise ValueError('Plan not found. Use different id')

    else:
        exists.name = new_name
        exists.updated_at = datetime.now(UTC)
        query_tool.commit()


def list_plans(marketplace):
    """
    Returns a list of plans currently in the database
    :param marketplace: The group/marketplace id/uri
    """
    results = query_tool(Plan).filter(Plan.marketplace == marketplace).all()
    return results


def delete_plan(plan_id, marketplace):
    """
    This method deletes a plan. Plans are not deleted from the database, but are instead marked as inactive so no new
    users can be added. Everyone currently on the plan
    :param plan_id: the unique plan_id
    :param marketplace: the plans marketplace/group
    :raise: ValueError if plan not found.
    """
    exists = query_tool(Plan).filter(Plan.plan_id == plan_id, Plan.marketplace == marketplace).first()
    if not exists:
        raise ValueError('Plan not found. Use different id')
    else:
        exists.active = False
        exists.updated_at = datetime.now(UTC)
        query_tool.commit()

