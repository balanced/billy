from __future__ import unicode_literals
import logging
import decimal

from billy.models import tables
from billy.models.plan import PlanModel
from billy.models.transaction import TransactionModel
from billy.models.schedule import next_transaction_datetime
from billy.utils.generic import make_guid


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
        started_at=None,
        external_id=None,
        discount=None,
    ):
        """Create a subscription and return its id

        """
        if discount is not None and discount < 0:
            raise ValueError('Discount should be a postive float number')
        if started_at is None:
            started_at = tables.now_func()
        # TODO: should we allow a past started_at value?
        subscription = tables.Subscription(
            guid='SU' + make_guid(),
            customer_guid=customer_guid,
            plan_guid=plan_guid,
            discount=discount, 
            external_id=external_id, 
            started_at=started_at, 
            next_transaction_at=started_at, 
        )
        self.session.add(subscription)
        self.session.flush()
        return subscription.guid

    def update(self, guid, **kwargs):
        """Update a subscription

        :param guid: the guid of subscription to update
        :param discount: discount to update
        :param external_id: external_id to update
        """
        subscription = self.get(guid, raise_error=True)
        now = tables.now_func()
        subscription.updated_at = now
        for key in ['discount', 'external_id']:
            if key not in kwargs:
                continue
            value = kwargs.pop(key)
            setattr(subscription, key, value)
        if kwargs:
            raise TypeError('Unknown attributes {} to update'.format(tuple(kwargs.keys())))
        self.session.add(subscription)
        self.session.flush()

    def cancel(self, guid, prorated_refund=False):
        """Cancel a subscription

        :param guid: the guid of subscription to cancel
        :param prorated_refund: Should we generate a prorated refund 
            transaction according to remaining time of subscription period?
        :return: if prorated_refund is True, and the subscription is 
            refundable, the refund transaction guid will be returned
        """
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
        if prorated_refund and subscription.period:
            previous_transaction = (
                self.session.query(tables.Transaction)
                .filter_by(subscription_guid=subscription.guid)
                .order_by(tables.Transaction.scheduled_at.desc())
                .first()
            )
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
            rate = elapsed_seconds / total_seconds
            amount = previous_transaction.amount * rate

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

    def yield_transactions(self, now=None):
        """Generate new necessary transactions according to subscriptions we 
        had return guid list

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
            subscriptions = (
                self.session.query(Subscription)
                .filter(Subscription.next_transaction_at <= now)
                .filter(not_(Subscription.canceled))
                .all()
            )

            # okay, we have no more transaction to process, just break
            if not subscriptions:
                break

            for subscription in subscriptions:
                if subscription.plan.plan_type == PlanModel.TYPE_CHARGE:
                    transaction_type = tx_model.TYPE_CHARGE
                elif subscription.plan.plan_type == PlanModel.TYPE_PAYOUT:
                    transaction_type = tx_model.TYPE_PAYOUT
                else:
                    raise ValueError('Unknown plan type {} to process'
                                     .format(subscription.plan.plan_type))
                amount = subscription.plan.amount 
                if subscription.discount is not None:
                    # TODO: what about float number round up?
                    amount *= (1 - subscription.discount)
                # create the new transaction for this subscription
                guid = tx_model.create(
                    subscription_guid=subscription.guid, 
                    payment_uri=subscription.customer.payment_uri, 
                    amount=amount, 
                    transaction_type=transaction_type, 
                    scheduled_at=subscription.next_transaction_at, 
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
