#DB SETTINGS
from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import sessionmaker


DB_SETTINGS = {
    'driver': 'postgresql',
    'host': 'localhost',
    'port': 5423,
    'user': 'test',
    'password': 'test',
    'db_name': 'billy',
}
POSTGRES_URL = URL(DB_SETTINGS['driver'], username=DB_SETTINGS['user'],
                   password=DB_SETTINGS['password'], port=DB_SETTINGS['port'],
                   database=DB_SETTINGS['db_name'])
DB_ENGINE = create_engine(POSTGRES_URL, echo=True)
DB_SESSION = sessionmaker(bind=DB_ENGINE)


#PROVIDER SETTINGS

#BILLING SETTINGS

#ETC
