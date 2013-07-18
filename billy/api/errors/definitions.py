from __future__ import unicode_literals

errors = {
    '401': {
        'status': 401,
        'error_message': 'UnAuthorized: Invalid API Key'
    },
}

for key in errors.keys():
    errors[key]['error_code'] = key
