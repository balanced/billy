from __future__ import unicode_literals
import binascii

from pyramid.httpexceptions import HTTPForbidden


def auth_api_key(request):
    """Authenticate API KEY and return corresponding company

    """
    company_model = request.model_factory.create_company_model()
    company = company_model.get_by_api_key(unicode(request.remote_user))
    if company is None:
        raise HTTPForbidden('Invalid API key {}'.format(request.remote_user))
    return company


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
