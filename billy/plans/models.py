from billy.models.base import Base, JSONDict
from sqlalchemy import Column, String, Integer, Boolean, DateTime
from sqlalchemy.schema import UniqueConstraint, ForeignKey
from sqlalchemy.orm import relationship
from pytz import UTC
from datetime import datetime
from dateutil.relativedelta import relativedelta
from billy.errors import BadIntervalError
from billy.customer.models import Customer
from billy.invoices.models import PlanInvoice
from billy.errors import NotFoundError, AlreadyExistsError
from sqlalchemy import and_
from decimal import Decimal



class Plan(Base):
    __tablename__ = 'plans'

    plan_id = Column(String, primary_key=True)
    marketplace = Column(String)
    name = Column(String)
    price_cents = Column(Integer)

    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=UTC), default=datetime.now(UTC))
    deleted_at = Column(DateTime(timezone=UTC))
    updated_at = Column(DateTime(timezone=UTC), default=datetime.now(UTC))
    trial_interval = Column(JSONDict)
    plan_interval = Column(JSONDict)
    customers = relationship(Customer.__name__, backref='plans')

    #Todo end of period
    __table_args__ = (
    UniqueConstraint('plan_id', 'marketplace', name='planid_marketplace'),
    )


    def __init__(self, id, marketplace, name, price_cents, plan_interval,
                 trial_interval):
        self.plan_id = id
        self.name = name
        self.price_cents = price_cents
        if not isinstance(plan_interval, relativedelta):
            raise BadIntervalError(
                "plan_interval must be a relativedelta type.")
        else:
            self.plan_interval = self.from_relativedelta(plan_interval)
        if not isinstance(trial_interval, relativedelta):
            raise BadIntervalError(
                "trial_interval must be a relativedelta type.")
        else:
            self.trial_interval = self.from_relativedelta(trial_interval)
        self.marketplace = marketplace

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
    def create_plan(cls, plan_id, marketplace, name, price_cents,
                    plan_interval, trial_interval):
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
        exists = cls.query.filter(and_(cls.plan_id == plan_id,
                               cls.marketplace == marketplace)).first()
        if not exists:
            new_plan = Plan(plan_id, marketplace, name, price_cents, plan_interval, trial_interval)
            cls.session.add(new_plan)
            cls.session.commit()
            return new_plan
        else:
            raise AlreadyExistsError('Plan already exists. Check plan_id and marketplace')

    @classmethod
    def retrieve_plan(cls, plan_id, marketplace, active_only=False):
        """
        This method retrieves a single plan.
        :param plan_id: the unique plan_id
        :param marketplace: the plans marketplace/group
        :param active_only: if true only returns active plans
        :raise NotFoundError:  if plan not found.
        """
        query = cls.query.filter(and_(cls.plan_id == plan_id,
                                       cls.marketplace == marketplace))
        if active_only:
            query.filter(cls.active == True)
        exists = query.first()
        if not exists:
            raise NotFoundError('Active Plan not found. Check plan_id and marketplace')
        return exists
    #Todo model methods


    @classmethod
    def update_plan(cls, plan_id, marketplace, new_name):
        """
        Updates ONLY the plan name. By design the only updateable field is the name.
        To change other params create a new plan.
        :param plan_id: The plan id/uri
        :param marketplace: The group/marketplace id/uri
        :param new_name: The new display name for the plan
        :raise NotFoundError:  if plan not found.
        :returns: New Plan object
        """
        exists = cls.query.filter(and_(cls.plan_id == plan_id,
                               cls.marketplace == marketplace)).first()
        if not exists:
            raise NotFoundError('Plan not found. Try different id')
        exists.name = new_name
        exists.updated_at = datetime.now(UTC)
        cls.session.commit()
        return exists

    @classmethod
    def list_plans(cls, marketplace):
        #Todo active only
        """
        Returns a list of plans currently in the database
        :param marketplace: The group/marketplace id/uri
        :returns: A list of Plan objects
        """
        results = cls.query.filter(cls.marketplace == marketplace).all()
        return results


    @classmethod
    def delete_plan(cls, plan_id, marketplace):
        """
        This method deletes a plan. Plans are not deleted from the database, but are instead marked as inactive so no new
        users can be added. Everyone currently on the plan is maintained on the plan.
        :param plan_id: the unique plan_id
        :param marketplace: the plans marketplace/group
        :returns: the deleted Plan object
        :raise NotFoundError:  if plan not found.
        """
        exists = cls.query.filter(and_(cls.plan_id == plan_id,
                               cls.marketplace == marketplace)).first()
        if not exists:
            raise NotFoundError('Plan not found. Use different id')
        exists.active = False
        exists.updated_at = datetime.now(UTC)
        exists.deleted_at = datetime.now(UTC)
        cls.session.commit()
        return exists

