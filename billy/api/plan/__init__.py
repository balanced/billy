from __future__ import unicode_literals


def includeme(config):
    config.add_route(
        name='plan_index', 
        pattern='/plans*traverse', 
        factory='billy.api.plan.views.plan_index_root',
    )
