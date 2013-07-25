from __future__ import unicode_literals

from api.resources.group import GroupController
from api.resources.customer import CustomerIndexController, CustomerController
from api.resources.coupon import CouponIndexController, CouponController


def get_methods(controller):
    methods = ['GET', 'POST', 'PUT', 'DELETE']
    method_list = []
    for method in methods:
        if hasattr(controller, method.lower()):
            try:
                doc = getattr(controller, method.lower()).__doc__.strip()
                method_list.append({
                    'method': method,
                    'description': doc,
                })
            except AttributeError, e:
                print "ERROR {} has no doc.".format(getattr(controller,
                                                      method.lower()))
                raise e

    return method_list


def get_doc(obj):
    return None if not obj.__doc__ else ' '.join(obj.__doc__.split()).strip()


billy_spec = {
    'group': {
        'path': '/auth/',
        'controller': GroupController,
    },
    'customers_index': {
        'path': '/customer/',
        'controller': CustomerIndexController,
    },
    'customer': {
        'path': '/customer/<string:customer_id>/',
        'controller': CustomerController,
    },
    'coupon_index': {
        'path': '/coupon/',
        'controller': CouponIndexController,
    },
    'coupon': {
        'path': '/coupon/<string:coupon_id>/',
        'controller': CouponController,
    }


}

billy_spec_processed = {}
for resource, spec in billy_spec.iteritems():
    spec['methods'] = get_methods(spec['controller'])
    spec['description'] = get_doc(spec['controller'])
    spec = spec.copy()
    del spec['controller']
    billy_spec_processed[resource] = spec

if __name__ == '__main__':
    import json

    with open('spec.json', 'w+') as spec_file:
        json.dump(billy_spec_processed, spec_file, indent=4)
    print('Spec written successfully.')