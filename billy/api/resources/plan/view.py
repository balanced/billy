from __future__ import unicode_literals

from billy.utils import fields
from billy.utils.intervals import IntervalViewField

plan_view = {
    # Todo: figure out why some arent showing...
    'id': fields.String(attribute='your_id'),
    'created_at': fields.DateTime(),
    'name': fields.String(),
    'price_cents': fields.Integer(),
    'active': fields.Boolean(),
    'plan_interval': IntervalViewField(),
    'trial_interval': IntervalViewField(),

}
