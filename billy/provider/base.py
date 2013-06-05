class BaseProvider(object):


    def __init__(self, api_key):
        self.api_key = api_key

    def check_balance(self):
        NotImplementedError("OVERWRITE THIS METHOD")

    def create_charge(self, customer, marketpalce, amount_cents):
        NotImplementedError('OVERWRITE THIS METHOD')

    def make_charge(self, customer, marketplace, amount_cents):
        NotImplementedError('OVERWRITE THIS METHOD')