from __future__ import unicode_literals

from api.resources.group import GroupController
from api.resources.customer import CustomerIndexController, CustomerController


def get_methods(controller):
    methods = ['GET', 'POST', 'PUT', 'DELETE']
    method_list = []
    for method in methods:
        if hasattr(controller, method.lower()):
            method_list.append(method)
    return method_list


billy_spec = {
    'group': {
        'path': '/auth/',
        'controller': GroupController,
        'methods': get_methods(GroupController),
        'description': "Base authentication route that converts an API key to"
                       " a group"
    },
    'customers_index': {
        'path': '/customer/',
        'controller': CustomerIndexController,
        'methods': get_methods(CustomerIndexController),
        'description': 'Returns a list of customers'
    },
    'customer': {
        'path': '/customer/<string:customer_id>/',
        'controller': CustomerController,
        'methods': get_methods(CustomerController),
        'description': 'Performs actions on a specific customer'

    }


}

billy_spec_processed = {}
for resource, spec in billy_spec.iteritems():
    spec = spec.copy()
    del spec['controller']
    billy_spec_processed[resource] = spec

if __name__ == '__main__':
    import json
    with open('spec.json', 'w+') as spec_file:
        json.dump(billy_spec_processed, spec_file, indent=4)
    print('Spec written successfully.')