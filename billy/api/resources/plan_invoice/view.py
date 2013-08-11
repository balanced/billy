from __future__ import unicode_literals

from billy.utils import fields

plan_inv_view = {
    # Todo: figure out why some arent showing...
    'id': fields.String(attribute='id'),
    'created_at': fields.DateTime(),
    'plan_id': fields.String(attribute='subscription.plan.your_id'),
    'customer_id': fields.String(attribute='subscription.customer.your_id'),
    'subscription_id': fields.String(attribute='subscription.id'),
    'relevant_coupon': fields.String(),
    'start_dt': fields.DateTime(),
    'end_dt': fields.DateTime(),
    'original_end_dt': fields.DateTime(),
    'prorated': fields.Boolean(),
    'charge_at_period_end': fields.Boolean(),
    'includes_trial': fields.Boolean(),
    'amount_base_cents': fields.Integer(),
    'amount_after_coupon_cents': fields.Integer(),
    'amount_paid_cents': fields.Integer(),
    'quantity': fields.Integer(),
    'remaining_balance_cents': fields.Integer(),
    'cleared_by_txn': fields.String(),
}
