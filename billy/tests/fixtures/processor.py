from __future__ import unicode_literals


class DummyProcessor(object):

    def __init__(self, processor_uri='MOCK_CUSTOMER_URI'):
        self.processor_uri = processor_uri

    def create_customer(self, customer):
        return self.processor_uri

    def validate_customer(self, processor_uri):
        return True

    def prepare_customer(self, customer, funding_instrument_uri=None):
        pass

    def charge(self, transaction):
        return 'MOCK_CHARGE_TX_ID'

    def payout(self, transaction):
        return 'MOCK_PAYOUT_TX_ID'

    def refund(self, transaction):
        return 'MOCK_REFUND_TX_ID'
