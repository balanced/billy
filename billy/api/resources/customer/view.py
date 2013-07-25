from __future__ import unicode_literals

from flask.ext.restful import fields

customer_view = {
    # Todo: figure out why customer_id isnt showing...
    'customer_id' : fields.String(attribute='external_id'),
    'created_at' : fields.DateTime(),
    'balanced_id' : fields.String(),
    'last_debt_clear' : fields.DateTime(),
    'charge_attempts' : fields.Integer(),

}