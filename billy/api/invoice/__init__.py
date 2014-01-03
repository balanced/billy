from __future__ import unicode_literals


def includeme(config):
    config.add_route('invoice', '/invoices/{invoice_guid}')
    config.add_route('invoice_list', '/invoices')
    config.add_route('invoice_transaction_list', '/invoice/{invoice_guid}/transactions')
