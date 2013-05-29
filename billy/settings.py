#DB SETTINGS
from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import sessionmaker

#DB SETTINGS
DB_SETTINGS = {
    'driver': 'postgresql',
    'host': 'localhost',
    'port': 5432,
    'user': 'test',
    'password': 'test',
    'db_name': 'billy',
}
POSTGRES_URL = URL(DB_SETTINGS['driver'], username=DB_SETTINGS['user'], host= DB_SETTINGS['host'],
                   password=DB_SETTINGS['password'], port=DB_SETTINGS['port'],
                   database=DB_SETTINGS['db_name'])

DB_ENGINE = create_engine(POSTGRES_URL)
Session = sessionmaker(bind=DB_ENGINE)
query_tool = Session()

