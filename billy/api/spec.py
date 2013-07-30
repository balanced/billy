from __future__ import unicode_literals

from flask.ext.restful import fields
from wtforms import fields as wtfields

from resources import *
from utils.intervals import IntervalViewField


def get_methods(controller):
    methods = ['GET', 'POST', 'PUT', 'DELETE']
    method_list = {}
    for method in methods:
        if hasattr(controller, method.lower()):
            try:
                doc = getattr(controller, method.lower()).__doc__.strip()
                method_list[method] = {
                    'description': doc,
                }
            except AttributeError, e:
                print "ERROR {} has no doc.".format(getattr(controller,
                                                            method.lower()))
                raise e

    return method_list


def get_view(view):
    field_map = {
        fields.String: 'STRING',
        fields.DateTime: 'DATETIME',
        fields.Integer: 'INTEGER',
        fields.Boolean: "BOOLEAN",
        IntervalViewField: 'INTERVAL',
    }
    if not view:
        return view
    data = {key: {'type': field_map[type(value)]} for key, value in
            view.iteritems()}
    return data


def get_doc(obj):
    return None if not obj.__doc__ else ' '.join(obj.__doc__.split()).strip()


def process_forms(spec_item):
    """
    Processes the forms in the spec items.
    """

    def process_form_class(form_class):
        field_map = {
            wtfields.TextField: 'STRING',
            wtfields.IntegerField: "INTEGER",
            wtfields.DateTimeField: "DATETIME",
            wtfields.BooleanField: "BOOLEAN"
        }
        return [{'name':name, 'type': field_map[type(field_class)]} for
                name, field_class in form_class()._fields.iteritems()]

    form = spec.get('form', {})
    for method, form_class in form.iteritems():
        method = method.upper()
        assert method in spec['methods'], "Method not in methods!"
        spec['methods'][method]['form_fields'] = process_form_class(form_class)
    return spec_item


billy_spec = {
    'group': {
        'path': '/auth/',
        'controller': GroupController
    },
    'customers_index': {
        'path': '/customer/',
        'controller': CustomerIndexController,
        'view': customer_view,
        'form': {
            'post': CustomerCreateForm
        }
    },
    'customer': {
        'path': '/customer/<string:customer_id>/',
        'controller': CustomerController,
        'view': customer_view,
        'form': {
            'put': CustomerUpdateForm
        }
    },
    'coupon_index': {
        'path': '/coupon/',
        'controller': CouponIndexController,
        'view': coupon_view,
        'form': {
            'post': CouponCreateForm
        }

    },
    'coupon': {
        'path': '/coupon/<string:coupon_id>/',
        'controller': CouponController,
        'view': coupon_view,
        'form': {
            'put': CouponUpdateForm
        }

    },
    'plan_index': {
        'path': '/plan/',
        'controller': PlanIndexController,
        'view': plan_view,
        'form': {
            'post': PlanCreateForm
        }

    },
    'plan': {
        'path': '/plan/<string:plan_id>/',
        'controller': PlanController,
        'view': plan_view,
        'form': {
            'put': PlanUpdateForm
        }

    },
    'payout_index': {
        'path': '/payout/',
        'controller': PayoutIndexController,
        'view': payout_view,
        'form': {
            'post': PayoutCreateForm
        }

    },
    'payout': {
        'path': '/payout/<string:payout_id>/',
        'controller': PayoutController,
        'view': payout_view,
        'form': {
            'put': PayoutUpdateForm
        }

    },
    'plan_subscription_index': {
        'path': '/plan_subscription/',
        'controller': PlanSubIndexController,
        'view': plan_sub_view,
        'form': {
            'post': PlanSubCreateForm,
            'delete': PlanSubDeleteForm
        }

    },
    'plan_subscription': {
        'path': '/plan_subscription/<string:plan_sub_id>/',
        'controller': PlanSubController,
        'view': plan_sub_view

    },
    'payout_subscription_index': {
        'path': '/payout_subscription/',
        'controller': PayoutSubIndexController,
        'view': payout_sub_view,
        'form': {
            'post': PayoutSubCreateForm,
            'delete': PlanSubDeleteForm
        }

    },
    'payout_subscription': {
        'path': '/payout_subscription/<string:payout_sub_id>/',
        'controller': PayoutSubController,
        'view': payout_sub_view

    },
    'plan_invoice_index': {
        'path': '/plan_invoice/',
        'controller': PlanInvIndexController,
        'view': plan_inv_view,

    },
    'plan_invoice': {
        'path': '/plan_invoice/<string:plan_inv_id>/',
        'controller': PlanInvController,
        'view': plan_inv_view

    },
    'payout_invoice_index': {
        'path': '/payout_invoice/',
        'controller': PayoutInvIndexController,
        'view': payout_inv_view

    },
    'payout_invoice': {
        'path': '/payout_invoice/<string:payout_inv_id>/',
        'controller': PayoutInvController,
        'view': payout_inv_view

    },
    'plan_transaction_index': {
        'path': '/plan_transaction/',
        'controller': PlanTransIndexController,
        'view': plan_trans_view

    },
    'plan_transaction': {
        'path': '/plan_transaction/<string:plan_trans_id>/',
        'controller': PlanTransController,
        'view': plan_trans_view

    },
    'payout_transaction_index': {
        'path': '/payout_transaction/',
        'controller': PayoutTransIndexController,
        'view': payout_trans_view

    },
    'payout_transaction': {
        'path': '/payout_transaction/<string:payout_trans_id>/',
        'controller': PayoutTransController,
        'view': payout_trans_view

    },

}

billy_spec_processed = {}
for resource, spec in billy_spec.iteritems():
    spec['methods'] = get_methods(spec['controller'])
    spec['description'] = get_doc(spec['controller'])
    spec['view'] = get_view(spec.get('view'))
    spec_new = process_forms(spec)
    del spec_new['controller']
    if 'form' in spec_new:
        del spec_new['form']
    billy_spec_processed[resource] = spec_new

if __name__ == '__main__':
    import json

    with open('spec.json', 'w+') as spec_file:
        json.dump(billy_spec_processed, spec_file, indent=4)
    print('Spec written successfully.')
