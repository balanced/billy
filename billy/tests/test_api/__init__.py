from __future__ import unicode_literals

from base64 import b64encode
import json
import os

from flask import url_for, Response
import jsonschema
from unittest import TestCase
from werkzeug.test import Client

from api.app import app
from api.errors import error_definitions
from api.resources import GroupController
from settings import TEST_API_KEYS


class ClientResponse(Response):
    def json(self):
        if self.content_type != 'application/json':
            error = 'content_type is not application/json! Got {0} instead.'
            raise TypeError(error.format(self.content_type))
        return json.loads(self.data.decode('utf-8'))


class TestClient(Client):
    def _add_headers(self, user, kwargs):
        if user and user.api_key:
            kwargs.setdefault('headers', {})['Authorization'] = \
                'Basic {}'.format(b64encode(':{}'.format(user.api_key)))
        return kwargs

    def get(self, url, user=None, *args, **kwargs):
        kwargs = self._add_headers(user, kwargs)
        return super(self.__class__, self).get(url, *args, **kwargs)

    def post(self, url, user=None, *args, **kwargs):
        kwargs = self._add_headers(user, kwargs)
        return super(self.__class__, self).post(url, *args, **kwargs)

    def put(self, url, user=None, *args, **kwargs):
        kwargs = self._add_headers(user, kwargs)
        return super(self.__class__, self).put(url, *args, **kwargs)

    def delete(self, url, user=None, *args, **kwargs):
        kwargs = self._add_headers(user, kwargs)
        return super(self.__class__, self).delete(url, *args, **kwargs)


class BaseTestCase(TestCase):
    json_schema_validator = jsonschema.Draft3Validator

    def setUp(self):
        super(BaseTestCase, self).setUp()
        self.api_key = TEST_API_KEYS[0]
        self.auth_headers = {
            'Authorization': 'Basic {}'.format(b64encode(
                ':{}'.format(self.api_key)))
        }

        self.client = TestClient(app, response_wrapper=ClientResponse)
        self.test_users = [
            type(str('group_user_{}'.format(i)), (), {'api_key': value}) for
            i, value in enumerate(TEST_API_KEYS)]
        self.ctx = app.test_request_context()
        self.ctx.push()
        for each_user in self.test_users:
            self.client.delete(self.url_for(GroupController), user=each_user)

    def url_for(self, controller, **kwargs):
        controller = controller.__name__.lower()
        return url_for(controller, **kwargs)

    def assertErrorMatches(self, resp, error_expected):
        definition = error_definitions[error_expected]
        resp_body = resp.json()
        self.assertEqual(resp.status_code, definition['status'])
        self.assertEqual(resp_body['status'], definition['status'])
        self.assertEqual(resp_body['error_message'],
                         definition['error_message'])
        self.assertEqual(resp_body['error_code'], error_expected)

    @classmethod
    def schemas_path(cls, file_name):
        base_path = os.path.dirname(__file__)
        return os.path.join(base_path, '../fixtures/schemas/', file_name)

    @classmethod
    def assertSchema(cls, to_check, schema_path):
        if isinstance(to_check, ClientResponse):
            to_check = to_check.json()
        with open(cls.schemas_path(schema_path)) as schema_file:
            schema = json.load(schema_file)
        cls.json_schema_validator(schema).validate(to_check)
