from __future__ import unicode_literals


def includeme(config):
    config.add_route('plan', '/plans/{plan_guid}')
    config.add_route('plan_list', '/plans')
