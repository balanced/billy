from __future__ import unicode_literals


def includeme(config):
    config.add_route('plan', '/plans/{plan_guid}')
    config.add_route('plan_list', '/plans')
    config.add_route('plan_customer_list', '/plans/{plan_guid}/customers')
    config.add_route('plan_subscription_list', '/plans/{plan_guid}/subscriptions')
    config.add_route('plan_transaction_list', '/plans/{plan_guid}/transactions')
