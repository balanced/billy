from __future__ import unicode_literals
import logging
import decimal

from billy.models import tables
from billy.models.plan import PlanModel
from billy.models.transaction import TransactionModel
from billy.models.schedule import next_transaction_datetime
from billy.utils.generic import make_guid
from billy.utils.generic import round_down_cent


class SubscriptionCanceledError(RuntimeError):
    """This error indicates that the subscription is already canceled,
    you cannot cancel a canceled subscription

    """


class SubscriptionModel(object):

    def __init__(self, session, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.session = session

    def get(self, guid, raise_error=False):
        """Find a subscription by guid and return it

        :param guid: The guild of subscription to get
        :param raise_error: Raise KeyError when cannot find one
        """
        query = (
            self.session.query(tables.Subscription)
            .filter_by(guid=guid)
            .first()
        )
        if raise_error and query is None:
            raise KeyError('No such subscription {}'.format(guid))
        return query

    def create(
        self, 
        customer_guid, 
        plan_guid, 
        payment_uri=None, 
        started_at=None,
        external_id=None,
        amount=None,
    ):
        """Create a subscription and return its id

        """
        if amount is not None and amount <= 0:
            raise ValueError('Amount should be a non-zero postive float number')
        now = tables.now_func()
        if started_at is None:
            started_at = now
        elif started_at < now:
            raise ValueError('Past started_at time is not allowed')
        subscription = tables.Subscription(
            guid='SU' + make_guid(),
            customer_guid=customer_guid,
            plan_guid=plan_guid,
            amount=amount, 
            payment_uri=payment_uri, 
            external_id=external_id, 
            started_at=started_at, 
            next_transaction_at=started_at, 
            created_at=now,
            updated_at=now,
        )
        self.session.add(subscription)
        self.session.flush()
        return subscription.guid

    def update(self, guid, **kwargs):
        """Update a subscription

        :param guid: the guid of subscription to update
        :param external_id: external_id to update
        """
        subscription = self.get(guid, raise_error=True)
        now = tables.now_func()
        subscription.updated_at = now
        for key in ['external_id']:
            if key not in kwargs:
                continue
            value = kwargs.pop(key)
            setattr(subscription, key, value)
        if kwargs:
            raise TypeError('Unknown attributes {} to update'.format(tuple(kwargs.keys())))
        self.session.add(subscription)
        self.session.flush()

    def cancel(self, guid, prorated_refund=False, refund_amount=None):
        """Cancel a subscription

        :param guid: the guid of subscription to cancel
        :param prorated_refund: Should we generate a prorated refund 
            transaction according to remaining time of subscription period?
        :param refund_amount: if refund_amount is given, it will be used 
            to refund customer, you cannot set prorated_refund with 
            refund_amount
        :return: if prorated_refund is True, and the subscription is 
            refundable, the refund transaction guid will be returned
        """
        if prorated_refund and refund_amount is not None:
            raise ValueError('You cannot set refund_amount when '
                             'prorated_refund is True')

        subscription = self.get(guid, raise_error=True)
        if subscription.canceled:
            raise SubscriptionCanceledError('Subscription {} is already '
                                            'canceled'.format(guid))
        now = tables.now_func()
        subscription.canceled = True
        subscription.canceled_at = now
        tx_guid = None
        # we want to do a prorated refund here, however, if there is no any 
        # issued transaction, then no need to do a refund, just skip
        if (
            (prorated_refund or refund_amount is not None) and 
            subscription.period
        ):
            previous_transaction = (
                self.session.query(tables.Transaction)
                .filter_by(subscription_guid=subscription.guid)
                .order_by(tables.Transaction.scheduled_at.desc())
                .first()
            )
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

            tx_model = TransactionModel(self.session)
            # make sure we will not refund zero dollar
            # TODO: or... should we?
            if amount:
                tx_guid = tx_model.create(
                    subscription_guid=subscription.guid, 
                    amount=amount, 
                    transaction_type=tx_model.TYPE_REFUND, 
                    scheduled_at=subscription.next_transaction_at, 
                    refund_to_guid=previous_transaction.guid, 
                )

        self.session.add(subscription)
        self.session.flush()
        return tx_guid 

    def yield_transactions(self, subscription_guids=None, now=None):
        """Generate new necessary transactions according to subscriptions we 
        had return guid list

        :param subscription_guids: A list subscription guid to yield 
            transaction_type from, if None is given, all subscriptions
            in the database will be the yielding source
        :param now: the current date time to use, now_func() will be used by 
            default
        :return: a generated transaction guid list
        """
        from sqlalchemy.sql.expression import not_

        if now is None:
            now = tables.now_func()

        tx_model = TransactionModel(self.session)
        Subscription = tables.Subscription

        transaction_guids = []

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
            if subscription_guids is not None:
                query = query.filter(Subscription.guid.in_(subscription_guids))
            subscriptions = query.all()

            # okay, we have no more transaction to process, just break
            if not subscriptions:
                self.logger.info('No more subscriptions to process')
                break

            for subscription in subscriptions:
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
                    'payment_uri=%s, amount=%s, scheduled_at=%s, period=%s', 
                    subscription.guid, 
                    type_map[transaction_type],
                    subscription.payment_uri,
                    amount,
                    subscription.next_transaction_at, 
                    subscription.period, 
                )
                # create the new transaction for this subscription
                guid = tx_model.create(
                    subscription_guid=subscription.guid, 
                    payment_uri=subscription.payment_uri, 
                    amount=amount, 
                    transaction_type=transaction_type, 
                    scheduled_at=subscription.next_transaction_at, 
                )
                self.logger.info(
                    'Created transaction for %s, guid=%s, transaction_type=%s, '
                    'payment_uri=%s, amount=%s, scheduled_at=%s, period=%s', 
                    subscription.guid, 
                    guid,
                    type_map[transaction_type],
                    subscription.payment_uri,
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
                transaction_guids.append(guid)

        self.session.flush()
        return transaction_guids
