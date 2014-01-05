from __future__ import unicode_literals


def includeme(config):
    config.add_route(
        name='transaction_index', 
        pattern='/transactions*traverse', 
        factory='billy.api.transaction.views.transaction_index_root',
    )
