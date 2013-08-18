from __future__ import unicode_literals

from sqlalchemy import engine_from_config
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from zope.sqlalchemy import ZopeTransactionExtension
    

from sqlalchemy import engine_from_config
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from zope.sqlalchemy import ZopeTransactionExtension
    

def setup_database(**settings):
    """Setup database
    
    """
    if 'engine' not in settings:
        settings['engine'] = \
            engine_from_config(settings, 'sqlalchemy.')
  
    if 'session' not in settings:
        settings['session'] = scoped_session(sessionmaker(
            extension=ZopeTransactionExtension(),
            bind=settings['engine']
        ))

    # SQLite does not support utc_timestamp function, therefore, we need to
    # replace it with utcnow of datetime here
    if settings['engine'].name == 'sqlite':
        import datetime
        from . import tables
        tables.set_now_func(datetime.datetime.utcnow)
        
    return settings
