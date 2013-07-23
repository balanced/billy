from __future__ import unicode_literals

from flask.ext.script import Manager

from models import *
from api.app import app
from settings import DB_ENGINE, DEBUG

manager = Manager(app)


@manager.command
def create_tables():
    """
    Creates the tables if they dont exists
    """
    Base.metadata.create_all(DB_ENGINE)


@manager.command
def delete_and_replace_tables():
    """
    Deletes and replaces the tables.
    Warning very destructive on production data.
    """
    assert DEBUG
    for table in Base.metadata.sorted_tables:
        table.delete()
    create_tables()


@manager.command
def main_task():
    """
    The main billy task that does EVERYTHING cron related.
    """
    Coupon.expire_coupons()
    PlanInvoice.clear_all_plan_debt()
    PlanInvoice.rollover_all()
    PayoutInvoice.make_all_payouts()
    PayoutInvoice.rollover_all()





if __name__ == "__main__":
    manager.run()
