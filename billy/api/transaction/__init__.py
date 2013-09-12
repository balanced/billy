from __future__ import unicode_literals


def includeme(config):
    config.add_route('transaction_list', '/transactions')
    config.add_route('transaction', '/transactions/{transaction_guid}')
