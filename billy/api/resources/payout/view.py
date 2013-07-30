from __future__ import unicode_literals

from flask.ext.restful import fields

from utils.intervals import IntervalViewField

payout_view = {
    # Todo: figure out why some arent showing...
    'id': fields.String(attribute='external_id'),
    'created_at': fields.DateTime(),
    'name': fields.String(),
    'balance_to_keep_cents': fields.Integer(),
    'active': fields.Boolean(),
    'payout_interval': IntervalViewField(),
}
