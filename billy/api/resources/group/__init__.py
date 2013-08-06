from __future__ import unicode_literals

from api.resources import Base
from api.errors import BillyExc
from models import Company
from settings import TEST_API_KEYS


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
        result = self.get_group_from_api_key(self.api_key)
        if not result:
            raise BillyExc['401']
        return result

    def get_group_from_api_key(self, api_key):
        """
        Takes an API key and grabs the Company associated with it.
        If the test API key is used and the test group doesnt exists it creates
        one and returns it.
        :param api_key: The API key
        :return:
        """
        result = Company.query.filter(Company.api_key == api_key).first()
        if not result and api_key in TEST_API_KEYS:
            return Company.create(
                'MY_TEST_GROUP_{}'.format(TEST_API_KEYS.index(api_key)),
                processor_type='DUMMY', processor_api_key='SOME_API_KEY',
                api_key=api_key)
        return result

    def get(self):
        """
        Used to test api_key and authentication
        """
        resp = {
            'AUTH_SUCCESS': True,
            'GROUP_ID': '{}'.format(self.group.your_id)
        }
        return resp


    def delete(self):
        """
        Deletes a group. ONLY deletion of test groups allowed.
        """
        if self.group.is_test:
            self.group.delete()
        else:
            raise BillyExc['405_DELETE_NON_TEST_GROUP']

