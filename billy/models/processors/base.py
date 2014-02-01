from __future__ import unicode_literals


class PaymentProcessor(object):

    def configure_api_key(self, api_key):
        """Configure API key for the processor, you need to call this method
        before you call any other methods

        :param api_key: the API key to set
        """
        raise NotImplementedError

    def create_customer(self, customer):
        """Create the customer record in payment processor

        :param customer: the customer table object
        :return: external id of customer from processor
        """
        raise NotImplementedError

    def prepare_customer(self, customer, funding_instrument_uri=None):
        """Prepare customer for transaction, usually this would associate
        bank account or credit card to the customer

        :param customer: customer to be prepared
        :param funding_instrument_uri: URI of funding instrument to be attached
        """
        raise NotImplementedError

    def validate_customer(self, processor_uri):
        """Validate a given customer URI in processor

        :param processor_uri: Customer URI in processor to validate
        """
        raise NotImplementedError

    def validate_funding_instrument(self, funding_instrument_uri):
        """Validate a given fundint instrument URI in processor

        :param funding_instrument_uri: The funding instrument URI in processor
            to validate
        """
        raise NotImplementedError

    def debit(self, transaction):
        """Charge from a bank acount or credit card

        """
        raise NotImplementedError

    def credit(self, transaction):
        """Payout to a account

        """
        raise NotImplementedError

    def refund(self, transaction):
        """Refund a transaction

        """
        raise NotImplementedError
