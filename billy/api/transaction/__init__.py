from __future__ import unicode_literals


def includeme(config):
    config.add_route('transaction', '/transactions/{transaction_guid}')
