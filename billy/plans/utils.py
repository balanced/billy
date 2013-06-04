from dateutil.relativedelta import relativedelta
from models import Plan
from pytz import UTC
from datetime import datetime
from billy.errors import NotFoundError, AlreadyExistsError
from sqlalchemy import and_

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


def create_plan(plan_id, marketplace, name, price_cents, plan_interval, trial_interval):
    """
    Creates a plan that users can be assigned to.
    :param plan_id: A unique id/uri for the plan
    :param marketplace: a group/marketplace id/uri the user should be placed in (matches balanced payments marketplaces)
    :param name: A display name for the plan
    :param price_cents: Price in cents of the plan per interval. $1.00 = 100
    :param plan_interval: A Interval class that defines how frequently the charge the plan
    :param trial_interval: A Interval class that defines how long the initial trial is
    :return: Plan Object if success or raises error if not
    :raise AlreadyExistsError: if plan already exists
    :raise TypeError: if intervals are not relativedelta (Interval class)
    """
    exists = query_tool.query(Plan).filter(and_(Plan.plan_id == plan_id, Plan.marketplace == marketplace)).first()
    if not exists:
        new_plan = Plan(plan_id, marketplace, name, price_cents, plan_interval, trial_interval)
        query_tool.add(new_plan)
        query_tool.commit()
        return new_plan
    else:
        raise AlreadyExistsError('Plan already exists. Check plan_id and marketplace')


def retrieve_plan(plan_id, marketplace, active_only=False):
    """
    This method retrieves a single plan.
    :param plan_id: the unique plan_id
    :param marketplace: the plans marketplace/group
    :param active_only: if true only returns active plans
    :raise NotFoundError:  if plan not found.
    """
    if active_only:
        and_filter = and_(Plan.plan_id == plan_id, Plan.marketplace == marketplace, Plan.active == True)
    else:
        and_filter = and_(Plan.plan_id == plan_id, Plan.marketplace == marketplace)
    exists = query_tool.query(Plan).filter(and_filter).first()
    if not exists:
        raise NotFoundError('Active Plan not found. Check plan_id and marketplace')
    return exists


def update_plan(plan_id, marketplace, new_name):
    """
    Updates ONLY the plan name. By design the only updateable field is the name.
    To change other params create a new plan.
    :param plan_id: The plan id/uri
    :param marketplace: The group/marketplace id/uri
    :param new_name: The new display name for the plan
    :raise NotFoundError:  if plan not found.
    :returns: New Plan object
    """
    exists = query_tool.query(Plan).filter(and_(Plan.plan_id == plan_id, Plan.marketplace == marketplace)).first()
    if not exists:
        raise NotFoundError('Plan not found. Try different id')
    exists.name = new_name
    exists.updated_at = datetime.now(UTC)
    query_tool.commit()
    return exists


def list_plans(marketplace):
    #Todo active only
    """
    Returns a list of plans currently in the database
    :param marketplace: The group/marketplace id/uri
    :returns: A list of Plan objects
    """
    results = query_tool.query(Plan).filter(Plan.marketplace == marketplace).all()
    return results


def delete_plan(plan_id, marketplace):
    """
    This method deletes a plan. Plans are not deleted from the database, but are instead marked as inactive so no new
    users can be added. Everyone currently on the plan is maintained on the plan.
    :param plan_id: the unique plan_id
    :param marketplace: the plans marketplace/group
    :returns: the deleted Plan object
    :raise NotFoundError:  if plan not found.
    """
    exists = query_tool.query(Plan).filter(and_(Plan.plan_id == plan_id, Plan.marketplace == marketplace)).first()
    if not exists:
        raise NotFoundError('Plan not found. Use different id')
    exists.active = False
    exists.updated_at = datetime.now(UTC)
    exists.deleted_at = datetime.now(UTC)
    query_tool.commit()
    return exists

