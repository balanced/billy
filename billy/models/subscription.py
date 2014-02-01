from __future__ import unicode_literals

from sqlalchemy.sql.expression import not_

from billy.db import tables
from billy.models.base import BaseTableModel
from billy.models.base import decorate_offset_limit
from billy.models.schedule import next_transaction_datetime
from billy.errors import BillyError
from billy.utils.generic import make_guid


class SubscriptionCanceledError(BillyError):
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
            next_invoice_at=started_at,
            created_at=now,
            updated_at=now,
        )
        self.session.add(subscription)
        self.session.flush()
        self.yield_invoices([subscription])
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

    def cancel(self, subscription):
        """Cancel a subscription

        :param subscription: the subscription to cancel
        """
        if subscription.canceled:
            raise SubscriptionCanceledError(
                'Subscription {} is already canceled'.format(subscription.guid)
            )
        now = tables.now_func()
        subscription.canceled = True
        subscription.canceled_at = now
        # TODO: what about refund?

    def yield_invoices(self, subscriptions=None, now=None):
        """Generate new scheduled invoices from given subscriptions

        :param subscriptions: A list subscription to yield invoices
            from, if None is given, all subscriptions in the database will be
            the yielding source
        :param now: the current date time to use, now_func() will be used by
            default
        :return: a generated transaction guid list
        """
        if now is None:
            now = tables.now_func()

        invoice_model = self.factory.create_invoice_model()
        Subscription = tables.Subscription

        subscription_guids = []
        if subscriptions is not None:
            subscription_guids = [
                subscription.guid for subscription in subscriptions
            ]
        invoices = []

        # as we may have multiple new invoices for one subscription to
        # yield now, for example, we didn't run this method for a long while,
        # in this case, we need to make sure all transactions are yielded
        while True:
            # find subscriptions which should yield new invoices
            query = (
                self.session.query(Subscription)
                .filter(Subscription.next_invoice_at <= now)
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
                amount = subscription.effective_amount
                # create the new transaction for this subscription
                invoice = invoice_model.create(
                    subscription=subscription,
                    funding_instrument_uri=subscription.funding_instrument_uri,
                    amount=amount,
                    scheduled_at=subscription.next_invoice_at,
                    appears_on_statement_as=subscription.appears_on_statement_as,
                )
                self.logger.info(
                    'Created subscription invoice for %s, guid=%s, '
                    'plan_type=%s, funding_instrument_uri=%s, '
                    'amount=%s, scheduled_at=%s, period=%s',
                    subscription.guid,
                    invoice.guid,
                    subscription.plan.plan_type,
                    invoice.funding_instrument_uri,
                    invoice.amount,
                    invoice.scheduled_at,
                    subscription.invoice_count - 1,
                )
                # advance the next invoice time
                subscription.next_invoice_at = next_transaction_datetime(
                    started_at=subscription.started_at,
                    frequency=subscription.plan.frequency,
                    period=subscription.invoice_count,
                    interval=subscription.plan.interval,
                )
                self.logger.info(
                    'Schedule next invoice of %s at %s (period=%s)',
                    subscription.guid,
                    subscription.next_invoice_at,
                    subscription.invoice_count,
                )
                self.session.flush()
                invoices.append(invoice)

        self.session.flush()
        return invoices
