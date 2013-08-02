from __future__ import unicode_literals

from utils import fields

plan_sub_view = {
    # Todo: figure out why some arent showing...
    'id': fields.String(attribute='guid'),
    'created_at': fields.DateTime(),
    'plan_id': fields.String(attribute='plan.external_id'),
    'customer_id': fields.String(attribute='customer.external_id'),
    'is_active': fields.Boolean(),
    'is_enrolled': fields.Boolean(),
    # Todo add invoices field
}
