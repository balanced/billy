from billy.models.base import Base, JSONDict
from sqlalchemy import Column, String, Integer, Boolean, DateTime
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.orm import relationship
from pytz import UTC
from datetime import datetime
from dateutil.relativedelta import relativedelta
from billy.errors import BadIntervalError
from billy.customer.models import Customers


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
    customers = relationship(Customers.__name__, backref='plans')

    __table_args__ = (UniqueConstraint('plan_id', 'marketplace', name='planid_marketplace'),
    )


    def __init__(self, id, marketplace, name, price_cents, plan_interval, trial_interval):
        self.plan_id = id
        self.name = name
        self.price_cents = price_cents
        if not isinstance(plan_interval, relativedelta):
            raise BadIntervalError("plan_interval must be a relativedelta type.")
        else:
            self.plan_interval = self.from_relativedelta(plan_interval)
        if not isinstance(trial_interval, relativedelta):
            raise BadIntervalError("trial_interval must be a relativedelta type.")
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
        return relativedelta(years=param['years'], months=param['months'], days=param['days'], hours=param['hours'],
                             minutes=param['minutes'])


