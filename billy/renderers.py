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


def includeme(config):
    json_renderer = JSON()
    json_renderer.add_adapter(tables.Company, company_adapter)
    json_renderer.add_adapter(tables.Customer, customer_adapter)
    config.add_renderer('json', json_renderer)
