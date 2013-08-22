from __future__ import unicode_literals


def includeme(config):
    config.add_route('customer', '/customers/{customer_guid}')
    config.add_route('customer_list', '/customers/')
