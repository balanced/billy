from __future__ import unicode_literals

from billy_lib.models import *
from billy_lib.settings import DB_ENGINE


def delete_and_replace_tables():
    for table in Base.metadata.sorted_tables:
        table.delete()
    create_if_notexists()


def create_if_notexists():
    Base.metadata.create_all(DB_ENGINE)
