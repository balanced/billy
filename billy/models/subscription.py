from __future__ import unicode_literals
import logging

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

    def get_subscription_by_guid(self, guid, raise_error=False):
        """Find a subscription by guid and return it

        :param guid: The guild of subscription to get
        :param raise_error: Raise KeyError when cannot find one
        """
        query = self.session.query(tables.Subscription) \
            .filter_by(guid=guid) \
            .first()
        if raise_error and query is None:
            raise KeyError('No such subscription {}'.format(guid))
        return query

    def create_subscription(
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

    def update_subscription(self, guid, **kwargs):
        """Update a subscription

        """
        subscription = self.get_subscription_by_guid(guid, raise_error=True)
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

    def cancel_subscription(self, guid, prorated_refund=False):
        """Cancel a subscription

        :param prorated_refund: Should we generate a prorated refund 
            transaction according to remaining time of subscription period?
        """
        subscription = self.get_subscription_by_guid(guid, raise_error=True)
        if subscription.canceled:
            raise SubscriptionCanceledError('Subscription {} is already '
                                            'canceled'.format(guid))
        now = tables.now_func()
        subscription.canceled = True
        subscription.canceled_at = now
        if prorated_refund:
            # TODO: handle prorated refund here
            pass
        self.session.add(subscription)
        self.session.flush()

    def yield_transactions(self, now=None):
        """Generate new necessary transactions according to subscriptions we 
        had return guid list

        :param now: the current date time to use, now_func() will be used by 
            default
        :return: generated transaction guid list
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
            query = self.session.query(Subscription) \
                .filter(Subscription.next_transaction_at <= now) \
                .filter(not_(Subscription.canceled))

            for subscription in query:
                if subscription.plan.plan_type == PlanModel.TYPE_CHARGE:
                    transaction_type = tx_model.TYPE_CHARGE
                elif subscription.plan.plan_type == PlanModel.TYPE_PAYOUT:
                    transaction_type = tx_model.TYPE_PAYOUT
                else:
                    raise ValueError('Unknown plan type {} to process'
                                     .format(subscription.plan.plan_type))
                # create the new transaction for this subscription
                guid = tx_model.create_transaction(
                    subscription_guid=subscription.guid, 
                    payment_uri=subscription.customer.payment_uri, 
                    amount=subscription.plan.amount, 
                    transaction_type=transaction_type, 
                    scheduled_at=subscription.next_transaction_at, 
                )
                # advance the next transaction time
                subscription.period += 1
                subscription.next_transaction_at = next_transaction_datetime(
                    started_at=subscription.started_at,
                    frequency=subscription.plan.frequency, 
                    period=subscription.period,
                )
                self.session.add(subscription)
                transaction_guids.append(guid)
            # okay, we have no more transaction to process, just break
            else:
                break

        self.session.flush()
        return transaction_guids
