#DB SETTINGS
from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import sessionmaker, scoped_session
from transactions.provider.balanced_payments import BalancedProvider


DB_SETTINGS = {
    'driver': 'postgresql',
    'host': 'localhost',
    'port': 5432,
    'user': 'test',
    'password': 'test',
    'db_name': 'billy',
    }

DB_URL = URL(DB_SETTINGS['driver'], username=DB_SETTINGS['user'],
        host= DB_SETTINGS['host'],
                   password=DB_SETTINGS['password'], port=DB_SETTINGS['port'],
                   database=DB_SETTINGS['db_name'])

DB_ENGINE = create_engine(DB_URL)
Session = scoped_session(sessionmaker(bind=DB_ENGINE))

TRANSACTION_PROVIDER_CLASS = BalancedProvider

