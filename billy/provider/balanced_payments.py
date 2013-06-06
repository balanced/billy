import random

from base import BaseProvider
from billy.utils.models import uuid_factory

class BalancedDummyProvider(BaseProvider):


    def check_balance(self):
        """
        Returns balance
        """
        return random.randint(100, 500000)


    def create_charge(self, customer, group, amount_cents):
        """
        Returns a transaction identifier or raises error
        """
        return uuid_factory('YOLO')()

    def make_payout(self, customer, group, amount_cents):
        """
        Returns a transaction identifier or raises error.
        """
        return uuid_factory('NOPE')()