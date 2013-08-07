from __future__ import unicode_literals

from utils import fields

payout_trans_view = {
    # Todo: figure out why some arent showing...
    'id': fields.String(attribute='id'),
    'created_at': fields.DateTime(),
    'invoices': fields.String(attribute='payout_invoices'),
    'customer_id': fields.String(),
    'amount_cents': fields.Integer(),
    'status': fields.String(),
    'provider_txn_id': fields.String(),
}
