from __future__ import unicode_literals

from billy.models import *
from billy.settings import DB_ENGINE


def delete_and_replace_tables():
    for table in Base.metadata.sorted_tables:
        table.delete()
    create_if_notexists()


def create_if_notexists():
    Base.metadata.create_all(DB_ENGINE)


create_if_notexists()
