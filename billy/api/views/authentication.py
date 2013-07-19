from __future__ import unicode_literals

from flask import request

from api.views import Base
from api.errors import BillyExc
from api.lib.auth import get_group_from_api_key


class AuthenticatedView(Base):
    """
    View to inherit from if authentication is needed. Raises 401 if Api key is
    inaccurate. Finds API Key in this order:
        1) HTTP Basic AUTH
        2) POST parameter
        3) GET query string parameter
    """
    api_key = None
    group = None

    def __init__(self):
        self.api_key = self.get_api_key_from_request()
        self.group = self.get_group_from_api_key()
        super(AuthenticatedView, self).__init__()

    def get_api_key_from_request(self):
        auth = request.authorization
        api_key = auth.get('password') if auth else \
            request.headers.get('Authorization')
        api_key = api_key or request.form.get('api_key') or \
                  request.args.get('api_key')
        return api_key

    def get_group_from_api_key(self):
        if not self.api_key:
            raise BillyExc['401']
        result = get_group_from_api_key(self.api_key)
        if not result:
            raise BillyExc['401']
        return result

    def get(self):
        resp = {
            'AUTH': 'GOOD',
            'GROUP_ID': '{}'.format(self.group.external_id)
        }
