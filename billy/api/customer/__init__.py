from __future__ import unicode_literals


def includeme(config):

    config.add_route(
        name='customer_index', 
        pattern='/customers*traverse', 
        factory='billy.api.customer.views.customer_index_root',
    )

    """
    config.add_route('customer_list', '/customers')

    config.add_route('customer_invoice_list', 
                     '/customers2/{customer_guid}/invoices')
    config.add_route('customer_subscription_list', 
                     '/customers2/{customer_guid}/subscriptions')
    config.add_route('customer_transaction_list', 
                     '/customers2/{customer_guid}/transactions')"""
