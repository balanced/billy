from __future__ import unicode_literals


def includeme(config):
    config.add_route(
        name='company_index', 
        pattern='/companies*traverse', 
        factory='billy.api.company.views.company_index_root',
    )
