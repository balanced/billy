from __future__ import unicode_literals
from datetime import datetime

from pytz import UTC
from sqlalchemy import Column, Unicode, Integer, Boolean, DateTime, \
    ForeignKey, UniqueConstraint
from sqlalchemy.orm import validates, relationship

from models.base import Base, RelativeDelta
from models.groups import Company
from utils.generic import uuid_factory


class ChargePlan(Base):
    __tablename__ = 'charge_plans'

    guid = Column(Unicode, primary_key=True, default=uuid_factory('PL'))
    external_id = Column(Unicode, nullable=False)
    group_id = Column(Unicode, ForeignKey(Company.guid), nullable=False)
    name = Column(Unicode, nullable=False)
    price_cents = Column(Integer, nullable=False)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    deleted_at = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.utcnow)
    trial_interval = Column(RelativeDelta)
    plan_interval = Column(RelativeDelta)

    subscriptions = relationship('PlanSubscription', backref='plan',
                                 cascade='delete')

    __table_args__ = (UniqueConstraint(external_id, group_id,
                                       name='plan_id_group_unique'),
                      )

    @classmethod
    def create(cls, external_id, group_id, name, price_cents,
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
        :return: ChargePlan Object if success or raises error if not
        """
        new_plan = cls(
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

    @classmethod
    def retrieve(cls, external_id, group_id, active_only=False):
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
            query = query.filter(cls.active == True)
        return query.one()

    @classmethod
    def list(cls, group_id, active_only=False):
        """
        Returns a list of plans currently in the database
        :param group_id: The group id/uri
        :returns: A list of ChargePlan objects
        """
        query = cls.query.filter(cls.group_id == group_id)
        if active_only:
            query = query.filter(cls.active == True)
        return query.all()

    def update(self, name):
        """
        Updates ONLY the plan name. By design the only updateable field is
        the name.
        To change other params create a new plan.
        :param name: The new display name for the plan
        :raise NotFoundError:  if plan not found.
        :returns: New ChargePlan object
        """
        self.name = name
        self.updated_at = datetime.utcnow()
        self.session.commit()
        return self

    def delete(self):
        """
        This method deletes a plan. Plans are not deleted from the database,
        but are instead marked as inactive so no new
        users can be added. Everyone currently on the plan is maintained on
        the plan.
        :returns: the deleted ChargePlan object (self)
        """
        self.active = False
        self.updated_at = datetime.utcnow()
        self.deleted_at = datetime.utcnow()
        self.session.commit()
        return self


    def can_trial_charge_plan(self, charge_plan):
        """
        Whether a customer can trial a charge_plan(
        """
        from models import PlanSubscription

        count = PlanSubscription.query.filter(
            PlanSubscription.customer_id == self.guid,
            PlanSubscription.plan_id == charge_plan.guid
        ).count()
        return not bool(count)


    @validates('price_cents')
    def validate_price_cents(self, key, address):
        if not address > 0:
            raise ValueError("400_PRICE_CENTS")
        return address
