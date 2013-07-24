from __future__ import unicode_literals

from flask import request

from api.resources import Base
from api.errors import BillyExc
from api.lib.auth import get_group_from_api_key


class GroupController(Base):

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
        super(GroupController, self).__init__()
        self.api_key = self.api_key_from_request()
        self.group = self.pull_group_object()

    def pull_group_object(self):
        if not self.api_key:
            raise BillyExc['401']
        result = get_group_from_api_key(self.api_key)
        if not result:
            raise BillyExc['401']
        return result

    def get(self):
        """
        Get path for auth testing purposes
        """
        resp = {
            'AUTH_SUCCESS': True,
            'GROUP_ID': '{}'.format(self.group.external_id)
        }
        return resp
