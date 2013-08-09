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
    print "Create tables.... DONE"


@manager.command
def delete_and_replace_tables():
    """
    Deletes and replaces the tables.
    Warning very destructive on production data.
    """
    assert DEBUG
    for table in Base.metadata.sorted_tables:
        table.delete()
    print "Delete tables.... DONE"
    create_tables()


@manager.command
def billy_tasks():
    """
    The main billy task that does EVERYTHING cron related.
    """
    Coupon.expire_coupons()
    Customer.settle_all_charge_plan_debt()
    ChargePlanInvoice.reinvoice_all()
    PayoutPlanInvoice.make_all_payouts()
    PayoutPlanInvoice.reinvoice_all()
    print "Billy task.... DONE"


@manager.command
def run_api():
    app.debug = DEBUG
    app.run()


if __name__ == "__main__":
    manager.run()
