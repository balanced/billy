from datetime import datetime

from pytz import UTC
from dateutil.relativedelta import relativedelta
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Unicode, Integer, Boolean, DateTime, ForeignKey

from billy.models.base import Base, JSONDict
from billy.models.customers import Customer
from billy.models.groups import Group
from billy.utils.models import uuid_factory
from billy.errors import NotFoundError, AlreadyExistsError


class Plan(Base):
    __tablename__ = 'plans'

    guid = Column(Unicode, primary_key=True, default=uuid_factory('PL'))
    external_id = Column(Unicode, index=True)
    group_id = Column(Unicode, ForeignKey(Group.external_id), index=True)
    name = Column(Unicode)
    price_cents = Column(Integer)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=UTC), default=datetime.now(UTC))
    deleted_at = Column(DateTime(timezone=UTC))
    updated_at = Column(DateTime(timezone=UTC), default=datetime.now(UTC))
    trial_interval = Column(JSONDict)
    plan_interval = Column(JSONDict)
    customers = relationship(Customer.__name__, backref='plans')

    __table_args__ = (
        UniqueConstraint('external_id', 'group_id', name='planid_group_id'),
    )


    def from_relativedelta(self, inter):
        return {
            'years': inter.years,
            'months': inter.months,
            'days': inter.days,
            'hours': inter.hours,
            'minutes': inter.minutes
        }

    def to_relativedelta(self, param):
        return relativedelta(years=param['years'], months=param['months'],
                             days=param['days'], hours=param['hours'],
                             minutes=param['minutes'])


    @classmethod
    def create_plan(cls, external_id, group_id, name, price_cents,
                    plan_interval, trial_interval):
        """
        Creates a plan that users can be assigned to.
        :param external_id: A unique id/uri for the plan
        :param group_id: a group id/uri the user should be placed in
        :param name: A display name for the plan
        :param price_cents: Price in cents of the plan per interval. $1.00 = 100
        :param plan_interval: A Interval class that defines how frequently
        the charge the plan
        :param trial_interval: A Interval class that defines how long the
        initial trial is
        :return: Plan Object if success or raises error if not
        :raise AlreadyExistsError: if plan already exists
        :raise TypeError: if intervals are not relativedelta (Interval class)
        """
        exists = cls.query.filter(cls.external_id == external_id,
                                  cls.group_id == group_id).first()
        if not exists:
            new_plan = Plan(
                external_id=external_id,
                group_id=group_id,
                name=name,
                price_cents=price_cents,
                plan_interval=plan_interval,
                trial_interval=trial_interval
            )
            cls.session.add(new_plan)
            cls.session.commit()
            return new_plan
        else:
            raise AlreadyExistsError(
                'Plan already exists. Check external_id and group_id')

    @classmethod
    def retrieve_plan(cls, external_id, group_id, active_only=False):
        """
        This method retrieves a single plan.
        :param external_id: the unique external_id
        :param group_id: the plans group
        :param active_only: if true only returns active plans
        :raise NotFoundError:  if plan not found.
        """
        query = cls.query.filter(cls.external_id == external_id,
                                 cls.group_id == group_id)
        if active_only:
            query.filter(cls.active == True)
        exists = query.first()
        if not exists:
            raise NotFoundError(
                'Active Plan not found. Check external_id and group_id')
        return exists


    @classmethod
    def update_plan(cls, external_id, group_id, new_name):
        """
        Updates ONLY the plan name. By design the only updateable field is
        the name.
        To change other params create a new plan.
        :param external_id: The plan id/uri
        :param group_id: The group id/uri
        :param new_name: The new display name for the plan
        :raise NotFoundError:  if plan not found.
        :returns: New Plan object
        """
        exists = cls.query.filter(cls.external_id == external_id,
                                  cls.group_id == group_id).first()
        if not exists:
            raise NotFoundError('Plan not found. Try different id')
        exists.name = new_name
        exists.updated_at = datetime.now(UTC)
        cls.session.commit()
        return exists

    @classmethod
    def list_plans(cls, group_id, active_only=False):
        """
        Returns a list of plans currently in the database
        :param group_id: The group id/uri
        :returns: A list of Plan objects
        """
        query = cls.query.filter(cls.group_id == group_id)
        if active_only:
            query.filter(cls.active == True)
        return query.all()


    @classmethod
    def delete_plan(cls, external_id, group_id):
        """
        This method deletes a plan. Plans are not deleted from the database,
        but are instead marked as inactive so no new
        users can be added. Everyone currently on the plan is maintained on
        the plan.
        :param external_id: the unique plan id/uri
        :param group_id: the plans group id/uri
        :returns: the deleted Plan object
        :raise NotFoundError:  if plan not found.
        """
        exists = cls.query.filter(cls.external_id == external_id,
                                  cls.group_id == group_id).first()
        if not exists:
            raise NotFoundError('Plan not found. Use different id')
        exists.active = False
        exists.updated_at = datetime.now(UTC)
        exists.deleted_at = datetime.now(UTC)
        cls.session.commit()
        return exists

