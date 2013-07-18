from __future__ import unicode_literals

from flask import request

from api.views import Base
from api.errors import BillyExc


class AuthenticatedView(Base):

    api_key = None
    user = None

    def __init__(self):
        self.api_key = self.get_api_key_from_request()
        self.user = self.get_user_from_api_key()
        super(AuthenticatedView, self).__init__()

    def get_api_key_from_request(self):
        auth = request.authorization
        api_key = auth.get('password') if auth else \
            request.headers.get('Authorization')
        api_key = api_key or request.form.get('api_key') or \
            request.args.get('api_key')
        return api_key

    def get_user_from_api_key(self):
        if not self.api_key:
            raise BillyExc['401']
        result = Users.find_one({'api_key': self.api_key})
        if not result:
            raise BillyExc['401']
        return result
