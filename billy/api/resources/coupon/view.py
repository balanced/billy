from __future__ import unicode_literals

from utils import fields

coupon_view = {
    # Todo: figure out why coupon_id isnt showing...
    'coupon_id': fields.String(attribute='your_id'),
    'created_at': fields.DateTime(),
    'name': fields.String(),
    'expire_at': fields.DateTime(),
    'price_off_cents': fields.Integer(),
    'percent_off_int': fields.Integer(),
    'max_redeem': fields.Integer(),
    'repeating': fields.Integer(),
    'active': fields.Boolean(),

}
