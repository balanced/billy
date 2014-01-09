from __future__ import unicode_literals
import logging

import balanced

from billy.models.transaction import TransactionModel
from billy.models.processors.base import PaymentProcessor
from billy.errors import BillyError


class InvalidURIFormat(BillyError):
    """This error indicates the given customer URI is not in URI format.
    There is a very common mistake, we saw many users of Billy tried to pass
    GUID of a balanced customer entity instead of URI. 

    """


class BalancedProcessor(PaymentProcessor):

    def __init__(
        self, 
        customer_cls=balanced.Customer, 
        debit_cls=balanced.Debit,
        credit_cls=balanced.Credit,
        refund_cls=balanced.Refund,
        logger=None,
    ):
        self.logger = logger or logging.getLogger(__name__)
        self.customer_cls = customer_cls
        self.debit_cls = debit_cls
        self.credit_cls = credit_cls
        self.refund_cls = refund_cls

    def _to_cent(self, amount):
        return int(amount)

    def _configure_api_key(self, customer):
        api_key = customer.company.processor_key
        balanced.configure(api_key)

    def create_customer(self, customer):
        self._configure_api_key(customer)
        self.logger.debug('Creating Balanced customer for %s', customer.guid)
        record = self.customer_cls(**{
            'meta.billy_customer_guid': customer.guid, 
        }).save()
        self.logger.info('Created Balanced customer for %s', customer.guid)
        return record.uri

    def prepare_customer(self, customer, funding_instrument_uri=None):
        self._configure_api_key(customer)
        self.logger.debug('Preparing customer %s with funding_instrument_uri=%s', 
                          customer.guid, funding_instrument_uri)
        # when funding_instrument_uri is None, it means we are going to use the 
        # default funding instrument, just return
        if funding_instrument_uri is None:
            return
        # get balanced customer record
        balanced_customer = self.customer_cls.find(customer.processor_uri)
        if '/bank_accounts/' in funding_instrument_uri:
            self.logger.debug('Adding bank account %s to %s', 
                              funding_instrument_uri, customer.guid)
            balanced_customer.add_bank_account(funding_instrument_uri)
            self.logger.info('Added bank account %s to %s', 
                             funding_instrument_uri, customer.guid)
        elif '/cards/' in funding_instrument_uri:
            self.logger.debug('Adding credit card %s to %s', 
                              funding_instrument_uri, customer.guid)
            balanced_customer.add_card(funding_instrument_uri)
            self.logger.info('Added credit card %s to %s', 
                             funding_instrument_uri, customer.guid)
        else:
            raise ValueError('Invalid funding_instrument_uri {}'.format(funding_instrument_uri))

    def validate_customer(self, processor_uri):
        if not processor_uri.startswith('/v1/'):
            raise InvalidURIFormat(
                'The processor_uri of a Balanced customer should be something '
                'like /v1/customers/CU53OU5AWeOVqpnDts7kbUXE, but we received '
                '{}. Remember, it is an URI rather than GUID.'
                .format(repr(processor_uri))
            )
        self.customer_cls.find(processor_uri)
        return True

    def _get_resource_by_tx_guid(self, resource_cls, guid):
        """Get Balanced resource object by Billy transaction GUID and return
        it, if there is not such resource, None is returned

        """
        try:
            resource = (
                resource_cls.query
                .filter(**{'meta.billy.transaction_guid': guid})
                .one()
            )
        except balanced.exc.NoResultFound:
            resource = None
        return resource

    def _do_transaction(
        self, 
        transaction, 
        resource_cls, 
        method_name, 
        extra_kwargs
    ):
        customer = transaction.invoice.customer
        self._configure_api_key(customer)

        # do existing check before creation to make sure we won't duplicate 
        # transaction in Balanced service
        resource = self._get_resource_by_tx_guid(resource_cls, transaction.guid)
        # We already have a record there in Balanced, this means we once did
        # transaction, however, we failed to update database. No need to do
        # it again, just return the URI
        if resource is not None:
            self.logger.warn('Balanced transaction record for %s already '
                             'exist', transaction.guid)
            return resource.uri

        # TODO: handle error here
        # get balanced customer record
        balanced_customer = self.customer_cls.find(customer.processor_uri)

        # prepare arguments
        kwargs = dict(
            amount=self._to_cent(transaction.amount),
            description=(
                'Generated by Billy from invoice {}'
                .format(transaction.invoice.guid)
            ),
            meta={'billy.transaction_guid': transaction.guid},
        )
        if transaction.appears_on_statement_as is not None:
            kwargs['appears_on_statement_as'] = transaction.appears_on_statement_as
        kwargs.update(extra_kwargs)

        if transaction.transaction_type == TransactionModel.TYPE_REFUND:
            debit_transaction = transaction.reference_to
            debit = self.debit_cls.find(debit_transaction.processor_uri)
            method = getattr(debit, method_name)
        else:
            method = getattr(balanced_customer, method_name)

        self.logger.debug('Calling %s with args %s', method.__name__, kwargs)
        record = method(**kwargs)
        self.logger.info('Called %s with args %s', method.__name__, kwargs)
        return record.uri

    def charge(self, transaction):
        extra_kwargs = {}
        if transaction.funding_instrument_uri is not None:
            extra_kwargs['source_uri'] = transaction.funding_instrument_uri
        return self._do_transaction(
            transaction=transaction, 
            resource_cls=self.debit_cls,
            method_name='debit',
            extra_kwargs=extra_kwargs,
        )

    def payout(self, transaction):
        extra_kwargs = {}
        if transaction.funding_instrument_uri is not None:
            extra_kwargs['destination_uri'] = transaction.funding_instrument_uri
        return self._do_transaction(
            transaction=transaction, 
            resource_cls=self.credit_cls,
            method_name='credit',
            extra_kwargs=extra_kwargs,
        )

    def refund(self, transaction):
        return self._do_transaction(
            transaction=transaction, 
            resource_cls=self.refund_cls,
            method_name='refund',
            extra_kwargs={},
        )
