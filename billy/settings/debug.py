from __future__ import unicode_literals

from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import sessionmaker, scoped_session

from billy.utils.intervals import Intervals

DB_SETTINGS = {
    'driver': 'sqlite',
    'host': '//billy.db',
    'db_name': 'billy',
}

DB_URL = URL(DB_SETTINGS['driver'], 
             host=DB_SETTINGS['host'])

DB_URL = 'sqlite:///billy.db'

DB_ENGINE = create_engine(DB_URL, echo=True)
Session = scoped_session(sessionmaker(bind=DB_ENGINE))

# A list of attempt invervals, [ATTEMPT n DELAY INTERVAL,...]
RETRY_DELAY_PLAN = [
    Intervals.WEEK,
    Intervals.TWO_WEEKS,
    Intervals.MONTH
]

RETRY_DELAY_PAYOUT = [
    Intervals.DAY,
    Intervals.DAY * 3,
    Intervals.WEEK
]
