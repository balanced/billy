from __future__ import unicode_literals
from hashlib import md5
import random

from billy.utils.models import uuid_factory


class BalancedProcessor(object):
    def __init__(self, credential):
        self.credential = credential

    def get_company_id(self):
        """
        Returns the id of the company with the models.processor, this is a form of
        authentication
        """
        hash = md5()
        hash.update(self.credential)
        return hash.hexdigest()

    def can_add_customer(self, customer_id):
        """
        Checks if customer exists and has a funding instrument
        """
        return True

    def check_balance(self, customer_id):
        """
        Returns balance
        """
        return random.randint(100000, 500000)

    def create_charge(self, customer, amount_cents):
        """
        Returns a transaction identifier or raises error
        """
        return uuid_factory('CHDUMMY')()

    def make_payout(self, customer, amount_cents):
        """
        Returns a transaction identifier or raises error.
        """
        return uuid_factory('PODUMMY')()
