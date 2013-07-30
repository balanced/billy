from __future__ import unicode_literals

from flask.ext.restful import fields

payout_sub_view = {
    # Todo: figure out why some arent showing...
    'id': fields.String(attribute='guid'),
    'created_at': fields.DateTime(),
    'payout_id': fields.String(attribute='payout.external_id'),
    'customer_id': fields.String(attribute='customer.external_id'),
    'is_active': fields.Boolean(),
    # Todo add invoices field
}
