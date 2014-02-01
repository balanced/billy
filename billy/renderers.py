from __future__ import unicode_literals

from pyramid.renderers import JSON

from billy.db import tables
from billy.models.invoice import InvoiceModel


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
            amount=item.amount,
            type=item.type,
            quantity=item.quantity,
            volume=item.volume,
            unit=item.unit,
        ))
    adjustments = []
    for adjustment in invoice.adjustments:
        adjustments.append(dict(
            amount=adjustment.amount,
            reason=adjustment.reason,
        ))

    if invoice.invoice_type == InvoiceModel.types.SUBSCRIPTION:
        extra_args = dict(
            subscription_guid=invoice.subscription_guid,
            scheduled_at=invoice.scheduled_at.isoformat(),
        )
    elif invoice.invoice_type == InvoiceModel.types.CUSTOMER:
        extra_args = dict(
            customer_guid=invoice.customer_guid,
            external_id=invoice.external_id,
        )

    return dict(
        guid=invoice.guid,
        invoice_type=enum_symbol(invoice.invoice_type),
        transaction_type=enum_symbol(invoice.transaction_type),
        status=enum_symbol(invoice.status),
        created_at=invoice.created_at.isoformat(),
        updated_at=invoice.updated_at.isoformat(),
        amount=invoice.amount,
        effective_amount=invoice.effective_amount,
        total_adjustment_amount=invoice.total_adjustment_amount,
        title=invoice.title,
        appears_on_statement_as=invoice.appears_on_statement_as,
        funding_instrument_uri=invoice.funding_instrument_uri,
        items=items,
        adjustments=adjustments,
        **extra_args
    )


def plan_adapter(plan, request):
    return dict(
        guid=plan.guid,
        plan_type=enum_symbol(plan.plan_type),
        frequency=enum_symbol(plan.frequency),
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
    serialized_failures = [
        transaction_failure_adapter(f, request)
        for f in transaction.failures
    ]
    return dict(
        guid=transaction.guid,
        invoice_guid=transaction.invoice_guid,
        transaction_type=enum_symbol(transaction.transaction_type),
        submit_status=enum_symbol(transaction.submit_status),
        status=enum_symbol(transaction.status),
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


def enum_symbol(enum_value):
    if enum_value is None:
        return enum_value
    return str(enum_value).lower()


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
