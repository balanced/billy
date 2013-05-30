from billy.settings import DB_ENGINE
from billy.plans.models import Plan
from billy.coupons.models import Coupon

table_classes = [Plan, Coupon]


def delete_and_replace():
    for each in table_classes:
        each.__table__.drop(DB_ENGINE)
    create_if_notexists()

def create_if_notexists():
    for each in table_classes:
        each.__table__.create(DB_ENGINE, checkfirst=True)

