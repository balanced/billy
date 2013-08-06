from __future__ import unicode_literals

from utils import fields

payout_inv_view = {
    # Todo: figure out why some arent showing...
    'id': fields.String(attribute='id'),
    'created_at': fields.DateTime(),
    'payout_id': fields.String(attribute='subscription.payout.your_id'),
    'customer_id': fields.String(attribute='subscription.customer.your_id'),
    'subscription_id': fields.String(attribute='subscription.id'),
    'payout_dt': fields.DateTime(),
    'balance_at_exec': fields.Integer(),
    'amount_paid_out': fields.Integer(),
    'attempts_made': fields.Integer(),
    'cleared_by_txn': fields.String(),
}
