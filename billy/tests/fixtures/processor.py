from __future__ import unicode_literals


class DummyProcessor(object):

    def __init__(self, processor_uri='MOCK_CUSTOMER_URI'):
        self.processor_uri = processor_uri
        self.api_key = None

    def _check_api_key(self):
        assert self.api_key is not None

    def configure_api_key(self, api_key):
        self.api_key = api_key

    def create_customer(self, customer):
        self._check_api_key()
        return self.processor_uri

    def validate_customer(self, processor_uri):
        self._check_api_key()
        return True

    def validate_funding_instrument(self, funding_instrument_uri):
        self._check_api_key()
        return True

    def prepare_customer(self, customer, funding_instrument_uri=None):
        self._check_api_key()

    def debit(self, transaction):
        self._check_api_key()
        return 'MOCK_DEBIT_TX_ID'

    def credit(self, transaction):
        self._check_api_key()
        return 'MOCK_CREDIT_TX_ID'

    def refund(self, transaction):
        self._check_api_key()
        return 'MOCK_REFUND_TX_ID'
