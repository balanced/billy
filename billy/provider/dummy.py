from __future__ import unicode_literals
import random

from base import BaseProvider
from billy.utils.models import uuid_factory

class DummyProvider(BaseProvider):


    def check_balance(self, customer, group):
        """
        Returns balance
        """
        return random.randint(100, 500000)


    def create_charge(self, customer, group, amount_cents):
        """
        Returns a transaction identifier or raises error
        """
        return uuid_factory('CHDUMMY')()

    def make_payout(self, customer, group, amount_cents):
        """
        Returns a transaction identifier or raises error.
        """
        return uuid_factory('PODUMMY')()