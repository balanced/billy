from __future__ import unicode_literals

import transaction as db_transaction
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPNotFound
from pyramid.httpexceptions import HTTPForbidden
from pyramid.httpexceptions import HTTPBadRequest
from pyramid.httpexceptions import HTTPConflict

from billy.models.invoice import InvoiceModel
from billy.models.invoice import DuplicateExternalIDError
from billy.api.auth import auth_api_key
from billy.api.utils import validate_form
from billy.api.utils import list_by_ancestor
from .forms import InvoiceCreateForm
from .forms import InvoiceUpdateForm


def get_and_check_invoice(request, company):
    """Get and check permission to access an invoice

    """
    model = request.model_factory.create_invoice_model()
    guid = request.matchdict['invoice_guid']
    invoice = model.get(guid)
    if invoice is None:
        raise HTTPNotFound('No such invoice {}'.format(guid))
    if invoice.customer.company_guid != company.guid:
        raise HTTPForbidden('You have no permission to access invoice {}'
                            .format(guid))
    return invoice 


def parse_items(request, prefix, keywords):
    """This function parsed items from request in following form

        item_name1=a
        item_amount1=100
        item_name2=b
        item_amount2=999
        item_unit2=hours
        item_name3=foo
        item_amount3=123

    and return a list as [
        dict(title='a', amount='100'),
        dict(title='b', amount='999', unit='hours'),
        dict(title='foo', amount='123'),
    ]

    """
    # TODO: humm.. maybe it is not the best method to deals with multiple 
    # value parameters, but here we just make it works and make it better
    # later
    # TODO: what about format checking? length limitation? is amount integer?
    items = {}
    for key in request.params:
        for keyword in keywords:
            prefixed_keyword = prefix + keyword
            suffix = key[len(prefixed_keyword):]
            if not key.startswith(prefixed_keyword):
                continue
            try:
                item_num = int(suffix)
            except ValueError:
                continue
            item = items.setdefault(item_num, {})
            item[keyword] = request.params[key]
    keys = list(items)
    keys = sorted(keys)
    return [items[key] for key in keys]


@view_config(route_name='invoice_list', 
             request_method='GET', 
             renderer='json')
def invoice_list_get(request):
    """Get and return the list of invoice

    """
    company = auth_api_key(request)
    return list_by_ancestor(request, InvoiceModel, company)


@view_config(route_name='invoice_list', 
             request_method='POST', 
             renderer='json')
def invoice_list_post(request):
    """Create a new invoice 

    """
    company = auth_api_key(request)
    form = validate_form(InvoiceCreateForm, request)
    model = request.model_factory.create_invoice_model()
    customer_model = request.model_factory.create_customer_model()
    tx_model = request.model_factory.create_transaction_model()
    
    customer_guid = form.data['customer_guid']
    amount = form.data['amount']
    funding_instrument_uri = form.data.get('funding_instrument_uri')
    if not funding_instrument_uri:
        funding_instrument_uri = None
    title = form.data.get('title')
    if not title:
        title = None
    external_id = form.data.get('external_id')
    if not external_id:
        external_id = None
    appears_on_statement_as = form.data.get('appears_on_statement_as')
    if not appears_on_statement_as:
        appears_on_statement_as = None
    items = parse_items(
        request=request, 
        prefix='item_', 
        keywords=('type', 'name', 'total', 'amount', 'unit', 'quantity'),
    )
    if not items:
        items = None
    adjustments = parse_items(
        request=request, 
        prefix='adjustment_', 
        keywords=('total', 'reason'),
    )
    if not adjustments:
        adjustments = None
    # TODO: what about negative effective amount?

    customer = customer_model.get(customer_guid)
    if customer.company != company:
        return HTTPForbidden('Can only create an invoice for your own customer')
    if customer.deleted:
        return HTTPBadRequest('Cannot create an invoice for a deleted customer')
    
    try:
        with db_transaction.manager:
            invoice = model.create(
                customer=customer,
                amount=amount,
                funding_instrument_uri=funding_instrument_uri,
                title=title,
                items=items,
                adjustments=adjustments,
                external_id=external_id,
                appears_on_statement_as=appears_on_statement_as,
            )
    except DuplicateExternalIDError, e:
        return HTTPConflict(e.args[0])
    # funding_instrument_uri is set, just process all transactions right away
    if funding_instrument_uri is not None:
        transactions = list(invoice.transactions)
        if transactions:
            with db_transaction.manager:
                tx_model.process_transactions(transactions)
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


@view_config(route_name='invoice', 
             request_method='PUT', 
             renderer='json')
def invoice_put(request):
    """Update an invoice

    """
    company = auth_api_key(request)
    invoice = get_and_check_invoice(request, company)
    form = validate_form(InvoiceUpdateForm, request)
    model = request.model_factory.create_invoice_model()
    tx_model = request.model_factory.create_transaction_model()

    funding_instrument_uri = form.data.get('funding_instrument_uri')
    title = form.data.get('title')
    items = parse_items(
        request=request, 
        prefix='item_', 
        keywords=('type', 'name', 'total', 'amount', 'unit', 'quantity'),
    )

    kwargs = {}
    if title:
        kwargs['title'] = title
    if items:
        kwargs['items'] = items

    with db_transaction.manager:
        model.update(invoice, **kwargs)
        if funding_instrument_uri:
            transactions = model.update_funding_instrument_uri(invoice, funding_instrument_uri)

    # funding_instrument_uri is set, just process all transactions right away
    if funding_instrument_uri and transactions:
        with db_transaction.manager:
            tx_model.process_transactions(transactions)

    return invoice 
