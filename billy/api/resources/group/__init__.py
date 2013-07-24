from __future__ import unicode_literals

from flask import request

from api.resources import Base
from api.errors import BillyExc
from api.lib.auth import get_group_from_api_key


class GroupController(Base):
    """
    Base authentication route that converts an API key to a group
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
        Used to test api_key and authentication
        """
        resp = {
            'AUTH_SUCCESS': True,
            'GROUP_ID': '{}'.format(self.group.external_id)
        }
        return resp
