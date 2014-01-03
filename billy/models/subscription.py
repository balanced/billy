from __future__ import unicode_literals
import decimal

from sqlalchemy.sql.expression import not_

from billy.models import tables
from billy.models.base import BaseTableModel
from billy.models.base import decorate_offset_limit
from billy.models.plan import PlanModel
from billy.models.transaction import TransactionModel
from billy.models.schedule import next_transaction_datetime
from billy.utils.generic import make_guid
from billy.utils.generic import round_down_cent


class SubscriptionCanceledError(RuntimeError):
    """This error indicates that the subscription is already canceled,
    you cannot cancel a canceled subscription

    """


class SubscriptionModel(BaseTableModel):

    TABLE = tables.Subscription

    @decorate_offset_limit
    def list_by_context(self, context):
        """List subscriptions by a given context

        """
        Company = tables.Company
        Customer = tables.Customer
        Plan = tables.Plan
        Subscription = tables.Subscription

        query = self.session.query(Subscription)
        if isinstance(context, Plan):
            query = query.filter(Subscription.plan == context)
        elif isinstance(context, Customer):
            query = query.filter(Subscription.customer == context)
        elif isinstance(context, Company):
            query = (
                query
                .join(
                    Plan,
                    Plan.guid == Subscription.plan_guid,
                )
                .filter(Plan.company == context)
            )
        else:
            raise ValueError('Unsupported context {}'.format(context))

        query = query.order_by(Subscription.created_at.desc())
        return query

    def create(
        self, 
        customer, 
        plan, 
        funding_instrument_uri=None, 
        started_at=None,
        external_id=None,
        appears_on_statement_as=None,
        amount=None,
    ):
        """Create a subscription and return its id

        """
        if amount is not None and amount <= 0:
            raise ValueError('Amount should be a non-zero postive integer')
        now = tables.now_func()
        if started_at is None:
            started_at = now
        elif started_at < now:
            raise ValueError('Past started_at time is not allowed')
        subscription = tables.Subscription(
            guid='SU' + make_guid(),
            customer=customer,
            plan=plan,
            amount=amount, 
            funding_instrument_uri=funding_instrument_uri, 
            external_id=external_id, 
            appears_on_statement_as=appears_on_statement_as, 
            started_at=started_at, 
            next_transaction_at=started_at, 
            created_at=now,
            updated_at=now,
        )
        self.session.add(subscription)
        self.session.flush()
        return subscription

    def update(self, subscription, **kwargs):
        """Update a subscription

        :param external_id: external_id to update
        """
        now = tables.now_func()
        subscription.updated_at = now
        for key in ['external_id']:
            if key not in kwargs:
                continue
            value = kwargs.pop(key)
            setattr(subscription, key, value)
        if kwargs:
            raise TypeError('Unknown attributes {} to update'.format(tuple(kwargs.keys())))
        self.session.flush()

    def cancel(
        self, 
        subscription, 
        prorated_refund=False, 
        refund_amount=None, 
        appears_on_statement_as=None,
    ):
        """Cancel a subscription

        :param subscription: the subscription to cancel
        :param prorated_refund: Should we generate a prorated refund 
            transaction according to remaining time of subscription period?
        :param refund_amount: if refund_amount is given, it will be used 
            to refund customer, you cannot set prorated_refund with 
            refund_amount
        :param appears_on_statement_as: the statement to show on customer's 
            transaction record if a refund is issued
        :return: if prorated_refund is True, and the subscription is 
            refundable, the refund transaction guid will be returned
        """
        if prorated_refund and refund_amount is not None:
            raise ValueError('You cannot set refund_amount when '
                             'prorated_refund is True')

        tx_model = self.factory.create_transaction_model()
        Transaction = tables.Transaction
        SubscriptionTransaction = tables.SubscriptionTransaction

        if subscription.canceled:
            raise SubscriptionCanceledError(
                'Subscription {} is already canceled'.format(subscription.guid)
            )
        now = tables.now_func()
        subscription.canceled = True
        subscription.canceled_at = now
        transaction = None

        # TODO: what is the transaction is submitted but not really done
        # in processor?

        # should we do refund
        do_refund = False
        # we want to do a prorated refund here, however, if there is no any 
        # issued transaction, then no need to do a refund, just skip
        if (
            (prorated_refund or refund_amount is not None) and 
            subscription.period
        ):
            previous_transaction = (
                self.session.query(SubscriptionTransaction)
                .filter_by(subscription=subscription)
                .order_by(SubscriptionTransaction.scheduled_at.desc())
                .first()
            )
            # it is possible the previous transaction is failed or retrying,
            # so that we should only refund finished transaction
            if previous_transaction.status == TransactionModel.STATUS_DONE:
                do_refund = True

        if do_refund:
            if prorated_refund:
                previous_datetime = previous_transaction.scheduled_at
                # the total time delta in the period
                total_delta = (
                    subscription.next_transaction_at - previous_datetime
                )
                total_seconds = decimal.Decimal(total_delta.total_seconds())
                # the passed time so far since last transaction
                elapsed_delta = now - previous_datetime
                elapsed_seconds = decimal.Decimal(elapsed_delta.total_seconds())

                # TODO: what about calculate in different granularity here?
                #       such as day or hour granularity?
                rate = 1 - (elapsed_seconds / total_seconds)
                amount = previous_transaction.amount * rate
                amount = round_down_cent(amount)
            else:
                amount = round_down_cent(decimal.Decimal(refund_amount))
                if amount > previous_transaction.amount:
                    raise ValueError('refund_amount cannot be grather than '
                                     'subscription amount {}'
                                     .format(previous_transaction.amount))

            # make sure we will not refund zero dollar
            # TODO: or... should we?
            if amount:
                transaction = tx_model.create(
                    subscription=subscription, 
                    amount=amount, 
                    transaction_type=tx_model.TYPE_REFUND, 
                    transaction_cls=tx_model.CLS_SUBSCRIPTION, 
                    scheduled_at=subscription.next_transaction_at, 
                    refund_to=previous_transaction, 
                    appears_on_statement_as=appears_on_statement_as,
                )

        # cancel not done transactions (exclude refund transaction)

        not_done_transaction_guids = (
            self.session.query(SubscriptionTransaction.guid)
            .filter(SubscriptionTransaction.subscription == subscription)
            .filter(Transaction.transaction_type != TransactionModel.TYPE_REFUND)
            .filter(Transaction.status.in_([
                tx_model.STATUS_INIT,
                tx_model.STATUS_RETRYING,
            ]))
        )
        not_done_transactions = (
            self.session
            .query(Transaction)
            .filter(Transaction.guid.in_(not_done_transaction_guids))
        )
        not_done_transactions.update(dict(
            status=tx_model.STATUS_CANCELED,
            updated_at=now, 
        ), synchronize_session='fetch')

        self.session.flush()
        return transaction 

    def yield_transactions(self, subscriptions=None, now=None):
        """Generate new necessary transactions according to subscriptions we 
        had return guid list

        :param subscriptions: A list subscription to yield transaction
            from, if None is given, all subscriptions in the database will be 
            the yielding source
        :param now: the current date time to use, now_func() will be used by 
            default
        :return: a generated transaction guid list
        """
        if now is None:
            now = tables.now_func()

        tx_model = self.factory.create_transaction_model()
        Subscription = tables.Subscription

        subscription_guids = []
        if subscriptions is not None:
            subscription_guids = [
                subscription.guid for subscription in subscriptions
            ]
        transactions = []

        # as we may have multiple new transactions for one subscription to
        # process, for example, we didn't run this method for a long while,
        # in this case, we need to make sure all transactions are yielded
        while True:
            # find subscriptions which should yield new transactions
            query = (
                self.session.query(Subscription)
                .filter(Subscription.next_transaction_at <= now)
                .filter(not_(Subscription.canceled))
            )
            if subscription_guids:
                query = query.filter(Subscription.guid.in_(subscription_guids))
            query = list(query)

            # okay, we have no more subscription to process, just break
            if not query:
                self.logger.info('No more subscriptions to process')
                break

            for subscription in query:
                if subscription.plan.plan_type == PlanModel.TYPE_CHARGE:
                    transaction_type = tx_model.TYPE_CHARGE
                elif subscription.plan.plan_type == PlanModel.TYPE_PAYOUT:
                    transaction_type = tx_model.TYPE_PAYOUT
                else:
                    raise ValueError('Unknown plan type {} to process'
                                     .format(subscription.plan.plan_type))
                # when amount of subscription is given, we should use it
                # instead the one from plan
                if subscription.amount is None:
                    amount = subscription.plan.amount 
                else:
                    amount = subscription.amount
                type_map = {
                    tx_model.TYPE_CHARGE: 'charge',
                    tx_model.TYPE_PAYOUT: 'payout',
                }
                self.logger.debug(
                    'Creating transaction for %s, transaction_type=%s, '
                    'funding_instrument_uri=%s, amount=%s, scheduled_at=%s, period=%s', 
                    subscription.guid, 
                    type_map[transaction_type],
                    subscription.funding_instrument_uri,
                    amount,
                    subscription.next_transaction_at, 
                    subscription.period, 
                )
                # create the new transaction for this subscription
                transaction = tx_model.create(
                    subscription=subscription, 
                    funding_instrument_uri=subscription.funding_instrument_uri, 
                    amount=amount, 
                    transaction_type=transaction_type, 
                    transaction_cls=tx_model.CLS_SUBSCRIPTION, 
                    scheduled_at=subscription.next_transaction_at, 
                    appears_on_statement_as=subscription.appears_on_statement_as,
                )
                self.logger.info(
                    'Created transaction for %s, guid=%s, transaction_type=%s, '
                    'funding_instrument_uri=%s, amount=%s, scheduled_at=%s, period=%s', 
                    subscription.guid, 
                    transaction.guid,
                    type_map[transaction_type],
                    subscription.funding_instrument_uri,
                    amount,
                    subscription.next_transaction_at, 
                    subscription.period, 
                )
                # advance the next transaction time
                subscription.period += 1
                subscription.next_transaction_at = next_transaction_datetime(
                    started_at=subscription.started_at,
                    frequency=subscription.plan.frequency, 
                    period=subscription.period,
                    interval=subscription.plan.interval, 
                )
                self.session.add(subscription)
                self.session.flush()
                transactions.append(transaction)

        self.session.flush()
        return transactions
