from __future__ import unicode_literals

errors = {
    # GENERIC ERRORS
    '400': {
        'status': 400,
        'message': 'Please check your request parameters.'
    },

    # GROUP ERRORS
    '401': {
        'status': 401,
        'error_message': 'UnAuthorized: Invalid API Key'
    },

    # CUSTOMER ERRORS
    '404_CUSTOMER_NOT_FOUND': {
        'status': 404,
        'error_message': 'The customer you requested was not found.'
    },
    '409_CUSTOMER_ALREADY_EXISTS': {
        'status': 409,
        'error_message': 'Cannot perform POST on an existing customer. Use '
                         'PUT instead.'
    },

    '400_CUSTOMER_ID': {
        'status': 400,
        'error_message': 'Invalid customer_id. Please check.'
    }

}

for key in errors.keys():
    errors[key]['error_code'] = key
