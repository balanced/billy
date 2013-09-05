from __future__ import unicode_literals


def includeme(config):
    config.include('.company', route_prefix='/v1')
    config.include('.customer', route_prefix='/v1')
    config.include('.plan', route_prefix='/v1')
    config.include('.subscription', route_prefix='/v1')
    config.include('.transaction', route_prefix='/v1')
