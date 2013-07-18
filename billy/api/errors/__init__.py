from __future__ import unicode_literals

from flask import jsonify, make_response, abort as flask_abort
from werkzeug.exceptions import HTTPException

from definitions import errors


class FlaskErrorDict(dict):
    bound_error = None

    def response(self):
        if not self.bound_error:
            raise ValueError('Must first bind an error.')
        data = {
            'status': self.bound_error['status'],
            'error_code': self.bound_error['error_code'],
            'error_message': self.bound_error['error_message'],
            'data': {}
        }
        resp = make_response((jsonify(data), self.bound_error['status']))
        return HTTPException(response=resp)

    def __getitem__(self, item):
        error_body = super(FlaskErrorDict, self).__getitem__(item)
        self.bound_error = error_body
        return self.response()

    def __getattr__(self, item):
        return self[item]


BillyExc = FlaskErrorDict(errors)
