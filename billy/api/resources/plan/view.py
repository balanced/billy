from __future__ import unicode_literals

from utils import fields

from utils.intervals import IntervalViewField

plan_view = {
    # Todo: figure out why some arent showing...
    'id': fields.String(attribute='external_id'),
    'created_at': fields.DateTime(),
    'name': fields.String(),
    'price_cents': fields.Integer(),
    'active': fields.Boolean(),
    'plan_interval': IntervalViewField(),
    'trial_interval': IntervalViewField(),

}
