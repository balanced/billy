from __future__ import unicode_literals


def includeme(config):
    config.add_route('subscription', '/subscriptions/{subscription_guid}')
    config.add_route('subscription_cancel', 
                     '/subscriptions/{subscription_guid}/cancel')
    config.add_route('subscription_list', '/subscriptions')
    config.add_route('subscription_transaction_list', 
                     '/subscriptions/{subscription_guid}/transactions')
    config.add_route('subscription_customer_list', 
                     '/subscriptions/{subscription_guid}/customers')
