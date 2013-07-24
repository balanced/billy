from __future__ import unicode_literals
import random

from utils.generic import uuid_factory


class DummyProvider(object):

    def __init__(self, api_key):
        self.api_key = api_key

    def check_balance(self, customer, group):
        """
        Returns balance
        """
        return random.randint(100000, 500000)

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
