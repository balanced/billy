from billy.settings import DB_ENGINE
from billy.plans.models import Plan

table_classes = [Plan, ]


def delete_and_replace():
    for each in table_classes:
        each.__table__.drop(DB_ENGINE)
    create_if_notexists()

def create_if_notexists():
    for each in table_classes:
        each.__table__.create(DB_ENGINE, checkfirst=True)


