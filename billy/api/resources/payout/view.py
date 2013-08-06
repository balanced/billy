from __future__ import unicode_literals

from utils import fields
from utils.intervals import IntervalViewField

payout_view = {
    # Todo: figure out why some arent showing...
    'id': fields.String(attribute='your_id'),
    'created_at': fields.DateTime(),
    'name': fields.String(),
    'balance_to_keep_cents': fields.Integer(),
    'active': fields.Boolean(),
    'payout_interval': IntervalViewField(),
}
