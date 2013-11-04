from __future__ import unicode_literals

import transaction as db_transaction
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPNotFound
from pyramid.httpexceptions import HTTPForbidden
from pyramid.httpexceptions import HTTPBadRequest

from billy.models.invoice import InvoiceModel
from billy.models.customer import CustomerModel
from billy.api.auth import auth_api_key
from billy.api.utils import validate_form
from billy.api.utils import list_by_company_guid
from .forms import InvoiceCreateForm


def get_and_check_invoice(request, company):
    """Get and check permission to access an invoice

    """
    model = InvoiceModel(request.session)
    guid = request.matchdict['invoice_guid']
    invoice = model.get(guid)
    if invoice is None:
        raise HTTPNotFound('No such invoice {}'.format(guid))
    if invoice.customer.company_guid != company.guid:
        raise HTTPForbidden('You have no permission to access invoice {}'
                            .format(guid))
    return invoice 


@view_config(route_name='invoice_list', 
             request_method='GET', 
             renderer='json')
def invoice_list_get(request):
    """Get and return the list of invoice

    """
    return list_by_company_guid(request, InvoiceModel)


@view_config(route_name='invoice_list', 
             request_method='POST', 
             renderer='json')
def invoice_list_post(request):
    """Create a new invoice 

    """
    company = auth_api_key(request)
    form = validate_form(InvoiceCreateForm, request)
    model = InvoiceModel(request.session)
    customer_model = CustomerModel(request.session)
    
    customer_guid = form.data['customer_guid']
    amount = form.data['amount']
    payment_uri = form.data.get('payment_uri')
    if not payment_uri:
        payment_uri = None

    customer = customer_model.get(customer_guid)
    if customer.company_guid != company.guid:
        return HTTPForbidden('Can only create an invoice for your own customer')
    if customer.deleted:
        return HTTPBadRequest('Cannot create an invoice for a deleted customer')
    
    with db_transaction.manager:
        guid = model.create(
            customer_guid=customer_guid,
            amount=amount,
            payment_uri=payment_uri,
        )
    invoice = model.get(guid)
    return invoice 


@view_config(route_name='invoice', 
             request_method='GET', 
             renderer='json')
def invoice_get(request):
    """Get and return an invoice 

    """
    company = auth_api_key(request)
    invoice = get_and_check_invoice(request, company)
    return invoice 
