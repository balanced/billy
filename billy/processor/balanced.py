from __future__ import unicode_literals
import random

from utils.generic import uuid_factory


class BalancedProcessor(object):
    is_test_mode = True

    def __init__(self, api_key):
        self.api_key = api_key

    def get_company_id(self):
        """
        Returns the id of the company with the processor, this is a form of
        authentication
        """
        return uuid_factory('MP')()

    def can_add_customer(self, customer_id):
        """
        Checks if customer exists and has a funding instrument
        """
        return True

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
