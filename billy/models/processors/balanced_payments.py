import balanced

from billy.models.processors.base import PaymentProcessor


class BalancedProcessor(PaymentProcessor):

    def __init__(self, customer_cls=balanced.Customer, debit_cls=balanced.Debit):
        self.customer_cls = customer_cls
        self.debit_cls = debit_cls

    def _to_cent(self, amount):
        cent = amount * 100
        cent = int(cent)
        return cent

    def create_customer(self, customer):
        record = self.customer_cls(**{
            'meta.billy_customer_guid': customer.guid, 
        }).save()
        return record.id

    def prepare_customer(self, customer, payment_uri=None):
        if payment_uri is None:
            return
        record = customer_cls.find(customer.external_id)
        # TODO: add payment uri to customer

    def charge(self, transaction):
        # make sure we won't duplicate debit
        try:
            debit = (
                self.debit_cls.query
                .filter(**{'meta.billy_transaction_guid': transaction.guid})
                .one()
            )
        except balanced.exc.NoResultFound:
            debit = None
        # We already have a Debit there in Balanced, this means we once did
        # transaction, however, we failed to update database. No need to do
        # it again, just return the id
        if debit is not None:
            return debit.id

        # TODO: handle error here
        # get balanced customer record
        external_id = transaction.subscription.customer.external_id
        balanced_customer = self.customer_cls.find(external_id)

        # prepare arguments
        kwargs = {
            'amount': self._to_cent(transaction.amount),
            'meta.billy_transaction_guid': transaction.guid,
        }
        if transaction.payment_uri is not None:
            kwargs['source_uri'] = transaction.payment_uri

        # TODO: handle error here
        debit = balanced_customer.debit(**kwargs)
        return debit.id

    def payout(self, transaction_guid, payment_uri, amount):
        customer = customer_cls.find(payment_uri)
        customer.credit(amount=self._to_cent(amount))
