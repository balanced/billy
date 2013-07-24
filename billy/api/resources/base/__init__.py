from __future__ import unicode_literals

from flask import request
from flask.ext import restful


class Base(restful.Resource):

    """
    Base view class to do what you want with
    """
    def api_key_from_request(self):
            auth = request.authorization
            api_key = auth.get('password') if auth else \
                request.headers.get('Authorization')
            api_key = api_key or request.form.get('api_key') or \
                request.args.get('api_key')
            return api_key

    def param_from_request(self, param):
        return request.view_args.get(param) or \
               request.args.get(param) or request.form.get(param)

