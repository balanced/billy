from base import Base
from sqlalchemy import Column, String, Integer, Boolean, DateTime
from pytz import UTC
from datetime import datetime
from dateutil import relativedelta

class Plan(Base):
    __tablename__ = 'billy_plans'

    id = Column(String, primary_key=True)
    name = Column(String)
    amount_cents = Column(Integer)
    active = Column(Boolean)
    created_at = Column(DateTime, default=datetime.now(tz=UTC))
    deleted_at = Column(DateTime)
    trial_days = Column(Integer)
    years = Column(Integer)
    months = Column(Integer)
    days = Column(Integer)
    weeks = Column(Integer)
    seconds = Column(Integer)


    def __init__(self):
        pass
