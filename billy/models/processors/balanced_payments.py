from __future__ import unicode_literals
import balanced

from billy.models.processors.base import PaymentProcessor


class BalancedProcessor(PaymentProcessor):

    def __init__(
        self, 
        customer_cls=balanced.Customer, 
        debit_cls=balanced.Debit,
        credit_cls=balanced.Credit,
    ):
        self.customer_cls = customer_cls
        self.debit_cls = debit_cls
        self.credit_cls = credit_cls

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

    def _do_transaction(
        self, 
        transaction, 
        resource_cls, 
        method_name, 
        extra_kwargs
    ):
        # make sure we won't duplicate debit
        try:
            record = (
                resource_cls.query
                .filter(**{'meta.billy_transaction_guid': transaction.guid})
                .one()
            )
        except balanced.exc.NoResultFound:
            record = None
        # We already have a record there in Balanced, this means we once did
        # transaction, however, we failed to update database. No need to do
        # it again, just return the id
        if record is not None:
            return record.id

        # TODO: handle error here
        # get balanced customer record
        external_id = transaction.subscription.customer.external_id
        balanced_customer = self.customer_cls.find(external_id)

        # prepare arguments
        kwargs = {
            'amount': self._to_cent(transaction.amount),
            'meta.billy_transaction_guid': transaction.guid,
        }
        kwargs.update(extra_kwargs)
        # TODO: handle error here
        method = getattr(balanced_customer, method_name)
        record = method(**kwargs)
        return record.id

    def charge(self, transaction):
        extra_kwargs = {}
        if transaction.payment_uri is not None:
            extra_kwargs['source_uri'] = transaction.payment_uri
        return self._do_transaction(
            transaction=transaction, 
            resource_cls=self.debit_cls,
            method_name='debit',
            extra_kwargs=extra_kwargs,
        )

    def payout(self, transaction):
        extra_kwargs = {}
        if transaction.payment_uri is not None:
            extra_kwargs['destination_uri'] = transaction.payment_uri
        return self._do_transaction(
            transaction=transaction, 
            resource_cls=self.credit_cls,
            method_name='credit',
            extra_kwargs=extra_kwargs,
        )
