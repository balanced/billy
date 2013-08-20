class PaymentProcessor(object):

    def create_customer(self, customer):
        """Create the customer record in payment processor

        :param customer: the customer table object
        :return: external id of customer from processor
        """
        raise NotImplementedError

    def prepare_customer(self, customer, payment_uri=None):
        """Prepare customer for transaction, usually this would associate
        bank account or credit card to the customer

        :param customer: customer to be prepared
        :param payment_uri: payment URI to prepare
        """
        raise NotImplementedError

    def charge(self, transaction):
        """Charge from a bank acount or credit card

        """
        raise NotImplementedError

    def payout(self, transaction):
        """Payout to a account

        """
        raise NotImplementedError