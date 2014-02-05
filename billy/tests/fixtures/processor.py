from __future__ import unicode_literals

from billy.models.transaction import TransactionModel


class DummyProcessor(object):

    def __init__(self, processor_uri='MOCK_CUSTOMER_URI'):
        self.processor_uri = processor_uri
        self.api_key = None

    def _check_api_key(self):
        assert self.api_key is not None

    def configure_api_key(self, api_key):
        self.api_key = api_key

    def callback(self, company, payload):

        def update_db(model_factory):
            pass

        return update_db

    def register_callback(self, company, url):
        pass

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
        return dict(
            processor_uri='MOCK_DEBIT_TX_URI',
            status=TransactionModel.statuses.SUCCEEDED,
        )

    def credit(self, transaction):
        self._check_api_key()
        return dict(
            processor_uri='MOCK_CREDIT_TX_URI',
            status=TransactionModel.statuses.SUCCEEDED,
        )

    def refund(self, transaction):
        self._check_api_key()
        return dict(
            processor_uri='MOCK_REFUND_TX_URI',
            status=TransactionModel.statuses.SUCCEEDED,
        )
