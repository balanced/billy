from __future__ import unicode_literals

from pyramid.renderers import JSON

from billy.models import tables
from billy.models.invoice import InvoiceModel
from billy.models.plan import PlanModel
from billy.models.transaction import TransactionModel


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
        processor_uri=customer.processor_uri, 
        created_at=customer.created_at.isoformat(),
        updated_at=customer.updated_at.isoformat(),
        company_guid=customer.company_guid, 
        deleted=customer.deleted, 
    )


def invoice_adapter(invoice, request):
    items = []
    for item in invoice.items:
        items.append(dict(
            name=item.name,
            total=item.total,
            type=item.type,
            quantity=item.quantity,
            amount=item.amount,
            unit=item.unit,
        ))
    adjustments = []
    for adjustment in invoice.adjustments:
        adjustments.append(dict(
            total=adjustment.total,
            reason=adjustment.reason,
        ))
    status_map = {
        InvoiceModel.STATUS_INIT: 'init',
        InvoiceModel.STATUS_PROCESSING: 'processing',
        InvoiceModel.STATUS_SETTLED: 'settled',
        InvoiceModel.STATUS_CANCELED: 'canceled',
        InvoiceModel.STATUS_PROCESS_FAILED: 'process_failed',
        InvoiceModel.STATUS_REFUNDING: 'refunding',
        InvoiceModel.STATUS_REFUNDED: 'refunded',
        InvoiceModel.STATUS_REFUND_FAILED: 'refund_failed',
    }
    status = status_map[invoice.status]

    type_map = {
        InvoiceModel.TYPE_SUBSCRIPTION: 'subscription',
        InvoiceModel.TYPE_CUSTOMER: 'customer',
    }
    invoice_type = type_map[invoice.invoice_type]

    tx_type_map = {
        TransactionModel.TYPE_CHARGE: 'charge',
        TransactionModel.TYPE_PAYOUT: 'payout',
    }
    transaction_type = tx_type_map[invoice.transaction_type]

    if invoice.invoice_type == InvoiceModel.TYPE_SUBSCRIPTION:
        extra_args = dict(
            subscription_guid=invoice.subscription_guid,
            scheduled_at=invoice.scheduled_at.isoformat(),
        )
    elif invoice.invoice_type == InvoiceModel.TYPE_CUSTOMER:
        extra_args = dict(
            customer_guid=invoice.customer_guid,
            external_id=invoice.external_id,
        )

    return dict(
        guid=invoice.guid,
        invoice_type=invoice_type,
        transaction_type=transaction_type,
        status=status,
        created_at=invoice.created_at.isoformat(),
        updated_at=invoice.updated_at.isoformat(),
        amount=invoice.amount, 
        total_adjustment_amount=invoice.total_adjustment_amount, 
        title=invoice.title, 
        appears_on_statement_as=invoice.appears_on_statement_as, 
        funding_instrument_uri=invoice.funding_instrument_uri, 
        items=items,
        adjustments=adjustments,
        **extra_args
    )


def plan_adapter(plan, request):
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
        amount=plan.amount,
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
    return dict(
        guid=subscription.guid, 
        amount=subscription.amount,
        effective_amount=subscription.effective_amount,
        funding_instrument_uri=subscription.funding_instrument_uri,
        appears_on_statement_as=subscription.appears_on_statement_as,
        invoice_count=subscription.invoice_count,
        canceled=subscription.canceled,
        next_invoice_at=subscription.next_invoice_at.isoformat(),
        created_at=subscription.created_at.isoformat(),
        updated_at=subscription.updated_at.isoformat(),
        started_at=subscription.started_at.isoformat(),
        canceled_at=canceled_at,
        customer_guid=subscription.customer_guid,
        plan_guid=subscription.plan_guid,
    )


def transaction_adapter(transaction, request):
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

    serialized_failures = [
        transaction_failure_adapter(f, request) 
        for f in transaction.failures
    ]
    return dict(
        guid=transaction.guid, 
        invoice_guid=transaction.invoice_guid,
        transaction_type=transaction_type,
        status=status,
        amount=transaction.amount,
        funding_instrument_uri=transaction.funding_instrument_uri,
        processor_uri=transaction.processor_uri,
        appears_on_statement_as=transaction.appears_on_statement_as,
        failure_count=transaction.failure_count,
        failures=serialized_failures,
        created_at=transaction.created_at.isoformat(),
        updated_at=transaction.updated_at.isoformat(),
    )


def transaction_failure_adapter(transaction_failure, request):
    return dict(
        guid=transaction_failure.guid,
        error_message=transaction_failure.error_message,
        error_number=transaction_failure.error_number,
        error_code=transaction_failure.error_code,
        created_at=transaction_failure.created_at.isoformat(),
    )


def includeme(config):
    settings = config.registry.settings
    kwargs = {}
    cfg_key = 'api.json.pretty_print'
    pretty_print = settings.get(cfg_key, True)    
    if pretty_print:
        kwargs = dict(sort_keys=True, indent=4, separators=(',', ': '))

    json_renderer = JSON(**kwargs)
    json_renderer.add_adapter(tables.Company, company_adapter)
    json_renderer.add_adapter(tables.Customer, customer_adapter)
    json_renderer.add_adapter(tables.Invoice, invoice_adapter)
    json_renderer.add_adapter(tables.Plan, plan_adapter)
    json_renderer.add_adapter(tables.Subscription, subscription_adapter)
    json_renderer.add_adapter(tables.Transaction, transaction_adapter)
    json_renderer.add_adapter(tables.TransactionFailure, 
                              transaction_failure_adapter)
    config.add_renderer('json', json_renderer)
