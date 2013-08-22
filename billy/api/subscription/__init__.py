from __future__ import unicode_literals


def includeme(config):
    config.add_route('subscription', '/subscriptions/{subscription_guid}')
    config.add_route('subscription_list', '/subscriptions/')
