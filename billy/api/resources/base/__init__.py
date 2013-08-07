from __future__ import unicode_literals

from flask import request, Response
from flask.ext import restful

from api.errors import BillyExc


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

    def dispatch_request(self, *args, **kwargs):
        # Taken from flask
        # noinspection PyUnresolvedReferences
        meth = getattr(self, request.method.lower(), None)
        if meth is None and request.method == 'HEAD':
            meth = getattr(self, 'get', None)
        assert meth is not None, 'Unimplemented method %r' % request.method

        for decorator in self.method_decorators:
            meth = decorator(meth)

        resp = meth(*args, **kwargs)

        if isinstance(resp, Response):  # There may be a better way to test
            return resp

        representations = self.representations or {}

        # noinspection PyUnresolvedReferences
        for mediatype in self.mediatypes():
            if mediatype in representations:
                data, code, headers = unpack(resp)
                resp = representations[mediatype](data, code, headers)
                resp.headers['Content-Type'] = mediatype
                return resp

        return resp

    def form_error(self, errors):
        last_key = None
        for key, value in errors.iteritems():
            last_key = key
            exc_key = '400_{}'.format(key.upper())
            if BillyExc.get(exc_key):
                raise BillyExc[exc_key]
        raise Exception('Field error for {} not defined!'.format(last_key))


class Home(Base):

    def get(self):
        return {
            "Welcome to billy":
            "Checkout here {}".format(
            'https://www.github.com/balanced/billy')
        }
