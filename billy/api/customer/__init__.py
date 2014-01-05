from __future__ import unicode_literals


def includeme(config):
    config.add_route(
        name='customer_index', 
        pattern='/customers*traverse', 
        factory='billy.api.customer.views.customer_index_root',
    )
