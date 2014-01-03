from __future__ import unicode_literals


def includeme(config):
    config.add_route('customer', '/customers/{customer_guid}')
    config.add_route('customer_list', '/customers')
    config.add_route('customer_invoice_list', 
                     '/customers/{customer_guid}/invoices')
    config.add_route('customer_subscription_list', 
                     '/customers/{customer_guid}/subscriptions')
    config.add_route('customer_transaction_list', 
                     '/customers/{customer_guid}/transactions')
