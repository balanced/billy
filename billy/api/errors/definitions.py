from __future__ import unicode_literals

errors = {
    # GENERIC ERRORS
    '400': {
        'status': 400,
        'error_message': 'Please check your request parameters.'
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

    # COUPON ERRORS
    '404_COUPON_NOT_FOUND': {
        'status': 404,
        'error_message': 'The coupon you requested was not found.'
    },
    '409_COUPON_ALREADY_EXISTS': {
        'status': 409,
        'error_message': 'Cannot perform POST on an existing coupon. Use '
                         'PUT instead.'
    },
    '409_COUPON_MAX_REDEEM': {
        'status': 409,
        'error_message': 'The coupon has already been redeemed maximum times'
    },


    # PLAN ERRORS
    '404_PLAN_NOT_FOUND': {
        'status': 404,
        'error_message': 'The plan you requested was not found.'
    },
    '409_PLAN_ALREADY_EXISTS': {
        'status': 409,
        'error_message': 'Cannot perform POST on an existing plan. Use '
                         'PUT instead.'
    },

    # Payout ERRORS
    '404_PAYOUT_NOT_FOUND': {
        'status': 404,
        'error_message': 'The payout you requested was not found.'
    },
    '409_PAYOUT_ALREADY_EXISTS': {
        'status': 409,
        'error_message': 'Cannot perform POST on an existing payout. Use '
                         'PUT instead.'
    },

    # Plan Subscription Errors
    '404_PLAN_SUB_NOT_FOUND': {
        'status': 404,
        'error_message': 'The plan subscription you requested was not found.'
    },

    # Payout Subscription Errors
    '404_PAYOUT_SUB_NOT_FOUND': {
        'status': 404,
        'error_message': 'The payout subscription you requested was not found.'
    },

    # Plan Invoice Errors
    '404_PLAN_INV_NOT_FOUND': {
        'status': 404,
        'error_message': 'The plan invoice you requested was not found.'
    },

    # Payout Invoice Errors
    '404_PAYOUT_INV_NOT_FOUND': {
        'status': 404,
        'error_message': 'The payout invoice you requested was not found.'
    },


    # Plan Invoice Errors
    '404_PLAN_TRANS_NOT_FOUND': {
        'status': 404,
        'error_message': 'The plan transaction you requested was not found.'
    },

    # Payout Invoice Errors
    '404_PAYOUT_TRANS_NOT_FOUND': {
        'status': 404,
        'error_message': 'The payout transaction you requested was not found.'
    },

    # FIELD ERRORS
    # Todo Temp place holders until validators are fed into the error_messages
    '400_CUSTOMER_ID': {
        'status': 400,
        'error_message': 'Invalid customer_id. Please check.'
    },
    '400_COUPON_ID': {
        'status': 400,
        'error_message': 'Invalid coupon_id. Please check.'
    },
    '400_PLAN_ID': {
        'status': 400,
        'error_message': 'Invalid coupon_id. Please check.'
    },
    '400_PAYOUT_ID': {
        'status': 400,
        'error_message': 'Invalid coupon_id. Please check.'
    },
    '400_NAME': {
        'status': 400,
        'error_message': 'Invalid name. Please check.'
    },
    '400_MAX_REDEEM': {
        'status': 400,
        'error_message': 'Invalid max_redeem. Please check.'
    },
    '400_REPEATING': {
        'status': 400,
        'error_message': 'Invalid repeating. Please check.'
    },
    '400_EXPIRE_AT': {
        'status': 400,
        'error_message': 'Invalid expire_at. Please check.'
    },
    '400_PERCENT_OFF_INT': {
        'status': 400,
        'error_message': 'Invalid percent_off_int. Please check.'
    },
    '400_PRICE_OFF_CENTS': {
        'status': 400,
        'error_message': 'Invalid price_off_cents. Please check.'
    },
    '400_PRICE_CENTS': {
        'status': 400,
        'error_message': 'Invalid price_cents. Please check.'
    },
    '400_TRIAL_INTERVAL': {
        'status': 400,
        'error_message': 'Invalid trial_interval. Please check.'
    },
    '400_PLAN_INTERVAL': {
        'status': 400,
        'error_message': 'Invalid plan_interval. Please check.'
    },
    '400_PAYOUT_INTERVAL': {
        'status': 400,
        'error_message': 'Invalid payout_interval. Please check.'
    },
    '400_BALANCE_TO_KEEP_CENTS': {
        'status': 400,
        'error_message': 'Invalid balance_to_keep_cents. Please check.'
    },
    '400_QUANTITY': {
        'status': 400,
        'error_message': 'Invalid quantity. Please check.'
    },

}

for key in errors.keys():
    errors[key]['error_code'] = key
