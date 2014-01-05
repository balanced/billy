from __future__ import unicode_literals


def includeme(config):
    config.add_route(
        name='subscription_index', 
        pattern='/subscriptions*traverse', 
        factory='billy.api.subscription.views.subscription_index_root',
    )
