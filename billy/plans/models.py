from billy.models.base import Base
from sqlalchemy import Column, String, Integer, Boolean, DateTime
from pytz import UTC
from datetime import datetime
from dateutil.relativedelta import relativedelta

class Plan(Base):
    __tablename__ = 'plans'

    id = Column(String, primary_key=True, unique=True)
    marketplace = Column(String)
    name = Column(String)
    price_cents = Column(Integer)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now(tz=UTC))
    deleted_at = Column(DateTime)
    updated_at = Column(DateTime)
    trial_interval = Column(Integer)
    years = Column(Integer)
    months = Column(Integer)
    weeks = Column(Integer)
    days = Column(Integer)
    hours = Column(Integer)
    minutes = Column(Integer)


    def __init__(self, id, marketplace, name, price_cents, interval, trial_days):
        self.id = id
        self.name = name
        self.price_cents = price_cents
        if not isinstance(interval, relativedelta):
            raise TypeError("interval must be a relativedelta type.")
        else:
            self.from_relativedelta(interval)
        self.trial_days = trial_days
        self.marketplace = marketplace

    def from_relativedelta(self, delta):
        self.years = delta.years
        self.months = delta.months
        self.weeks = delta.weeks
        self.days = delta.days
        self.hours = delta.hours
        self.minutes = delta.minutes

    def to_relativedelta(self):
        return relativedelta(years=self.years, months=self.months,
                             weeks=self.weeks, days=self.days, hours=self.hours,
                             minutes=self.minutes)


