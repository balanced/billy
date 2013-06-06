class BaseProvider(object):


    def __init__(self, api_key):
        self.api_key = api_key

    def check_balance(self):
        """
        Returns balance
        """
        NotImplementedError("OVERWRITE THIS METHOD")

    def create_charge(self, customer, marketpalce, amount_cents):
        """
        Returns a transaction identifier or raises error
        """
        NotImplementedError('OVERWRITE THIS METHOD')

    def make_payout(self, customer, marketplace, amount_cents):
        """
        Returns a transaction identifier or raises error.
        """
        NotImplementedError('OVERWRITE THIS METHOD')