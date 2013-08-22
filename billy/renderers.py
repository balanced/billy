from __future__ import unicode_literals

from pyramid.renderers import JSON

from billy.models import tables


def company_adapter(company, request):
    return dict(
        guid=company.guid,
        api_key=company.api_key,
        created_at=company.created_at.isoformat(),
        updated_at=company.created_at.isoformat(),
    )


def customer_adapter(customer, request):
    return dict(
        guid=customer.guid,
        external_id=customer.external_id, 
        created_at=customer.created_at.isoformat(),
        updated_at=customer.created_at.isoformat(),
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
        updated_at=plan.created_at.isoformat(),
    )


def includeme(config):
    json_renderer = JSON()
    json_renderer.add_adapter(tables.Company, company_adapter)
    json_renderer.add_adapter(tables.Customer, customer_adapter)
    json_renderer.add_adapter(tables.Plan, plan_adapter)
    config.add_renderer('json', json_renderer)
