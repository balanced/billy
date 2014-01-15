from __future__ import unicode_literals
import binascii

from pyramid.security import Everyone
from pyramid.security import Authenticated


class AuthenticationPolicy(object):

    def authenticated_userid(self, request):
        api_key = self.unauthenticated_userid(request)
        if api_key is None:
            return None
        company_model = request.model_factory.create_company_model()
        company = company_model.get_by_api_key(api_key)
        return company

    def unauthenticated_userid(self, request):
        if request.remote_user:
            return unicode(request.remote_user)
        return None

    def effective_principals(self, request):
        effective_principals = [Everyone]

        api_key = self.unauthenticated_userid(request)
        if api_key is None:
            return effective_principals

        company = self.authenticated_userid(request)
        if company is not None:
            effective_principals.append(Authenticated)
            effective_principals.append('company:{}'.format(company.guid))
        return effective_principals

    def remember(self, request, principal, **kw):
        return []

    def forget(self, request):
        return []


def get_remote_user(request):
    """Parse basic HTTP_AUTHORIZATION and return user name

    """
    if 'HTTP_AUTHORIZATION' not in request.environ:
        return
    authorization = request.environ['HTTP_AUTHORIZATION']
    try:
        authmeth, auth = authorization.split(' ', 1)
    except ValueError:  # not enough values to unpack
        return
    if authmeth.lower() != 'basic':
        return
    try:
        auth = auth.strip().decode('base64')
    except binascii.Error:  # can't decode
        return
    try:
        login, password = auth.split(':', 1)
    except ValueError:  # not enough values to unpack
        return
    return login


def basic_auth_tween_factory(handler, registry):
    """Do basic authentication, parse HTTP_AUTHORIZATION and set remote_user
    variable to request

    """
    def basic_auth_tween(request):
        remote_user = get_remote_user(request)
        if remote_user is not None:
            request.remote_user = remote_user
        return handler(request)
    return basic_auth_tween
