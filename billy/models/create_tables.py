import sys
from billy.settings import DB_ENGINE
from billy.models.base import Base
from billy.invoices.models import PlanInvoice, PayoutInvoice


def delete_and_replace_tables():
    assert('test' in sys.argv)
    for table in Base.metadata.sorted_tables:
         table.delete()
    create_if_notexists()

def create_if_notexists():
    Base.metadata.create_all(DB_ENGINE)
