from __future__ import unicode_literals

from pyramid.renderers import JSON

from billy.models import tables


def company_adapter(company, request):
    return dict(
        guid=company.guid,
        api_key=company.api_key,
        created_at=company.created_at.isoformat(),
        updated_at=company.updated_at.isoformat(),
    )


def customer_adapter(customer, request):
    return dict(
        guid=customer.guid,
        external_id=customer.external_id, 
        created_at=customer.created_at.isoformat(),
        updated_at=customer.updated_at.isoformat(),
        company_guid=customer.company_guid, 
        deleted=customer.deleted, 
    )


def plan_adapter(plan, request):
    from billy.models.plan import PlanModel
    type_map = {
        PlanModel.TYPE_CHARGE: 'charge',
        PlanModel.TYPE_PAYOUT: 'payout',
    }
    plan_type = type_map[plan.plan_type]

    freq_map = {
        PlanModel.FREQ_DAILY: 'daily',
        PlanModel.FREQ_WEEKLY: 'weekly',
        PlanModel.FREQ_MONTHLY: 'monthly',
        PlanModel.FREQ_YEARLY: 'yearly',
    }
    frequency = freq_map[plan.frequency]
    return dict(
        guid=plan.guid, 
        plan_type=plan_type,
        frequency=frequency,
        amount=str(plan.amount),
        interval=plan.interval,
        created_at=plan.created_at.isoformat(),
        updated_at=plan.updated_at.isoformat(),
        company_guid=plan.company_guid,
        deleted=plan.deleted,
    )


def subscription_adapter(subscription, request):
    canceled_at = None
    if subscription.canceled_at is not None:
        canceled_at = subscription.canceled_at.isoformat()
    amount = None
    if subscription.amount is not None:
        amount = str(subscription.amount)
    return dict(
        guid=subscription.guid, 
        amount=amount,
        payment_uri=subscription.payment_uri,
        period=subscription.period,
        canceled=subscription.canceled,
        next_transaction_at=subscription.next_transaction_at.isoformat(),
        created_at=subscription.created_at.isoformat(),
        updated_at=subscription.updated_at.isoformat(),
        started_at=subscription.started_at.isoformat(),
        canceled_at=canceled_at,
        customer_guid=subscription.customer_guid,
        plan_guid=subscription.plan_guid,
    )


def transaction_adapter(transaction, request):
    from billy.models.transaction import TransactionModel
    type_map = {
        TransactionModel.TYPE_CHARGE: 'charge',
        TransactionModel.TYPE_PAYOUT: 'payout',
        TransactionModel.TYPE_REFUND: 'refund',
    }
    transaction_type = type_map[transaction.transaction_type]

    status_map = {
        TransactionModel.STATUS_INIT: 'init',
        TransactionModel.STATUS_RETRYING: 'retrying',
        TransactionModel.STATUS_FAILED: 'failed',
        TransactionModel.STATUS_DONE: 'done',
        TransactionModel.STATUS_CANCELED: 'canceled',
    }
    status = status_map[transaction.status]

    return dict(
        guid=transaction.guid, 
        transaction_type=transaction_type,
        status=status,
        amount=str(transaction.amount),
        payment_uri=transaction.payment_uri,
        external_id=transaction.external_id,
        failure_count=transaction.failure_count,
        error_message=transaction.error_message,
        created_at=transaction.created_at.isoformat(),
        updated_at=transaction.updated_at.isoformat(),
        scheduled_at=transaction.scheduled_at.isoformat(),
        subscription_guid=transaction.subscription_guid,
    )


def includeme(config):
    json_renderer = JSON()
    json_renderer.add_adapter(tables.Company, company_adapter)
    json_renderer.add_adapter(tables.Customer, customer_adapter)
    json_renderer.add_adapter(tables.Plan, plan_adapter)
    json_renderer.add_adapter(tables.Subscription, subscription_adapter)
    json_renderer.add_adapter(tables.Transaction, transaction_adapter)
    config.add_renderer('json', json_renderer)
