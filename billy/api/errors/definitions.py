from __future__ import unicode_literals

errors = {
    '401': {
        'status': 401,
        'error_message': 'UnAuthorized: Invalid API Key'
    },
    '404_CUSTOMER_NOT_FOUND': {
        'status': 401,
        'error_message': 'The customer you requested was not found.'
    }
}

for key in errors.keys():
    errors[key]['error_code'] = key
