from __future__ import unicode_literals


def includeme(config):
    config.add_route(
        name='invoice_index', 
        pattern='/invoices*traverse', 
        factory='billy.api.invoice.views.invoice_index_root',
    )
