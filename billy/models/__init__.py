from __future__ import unicode_literals
import datetime

from sqlalchemy import engine_from_config
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from zope.sqlalchemy import ZopeTransactionExtension
   
from . import tables


def setup_database(global_config, **settings):
    """Setup database
    
    """
    if 'engine' not in settings:
        settings['engine'] = (
            engine_from_config(settings, 'sqlalchemy.')
        )
  
    if 'session' not in settings:
        settings['session'] = scoped_session(sessionmaker(
            extension=ZopeTransactionExtension(keep_session=True),
            bind=settings['engine'],
        ))

    tables.set_now_func(datetime.datetime.utcnow)
    return settings
