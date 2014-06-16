from __future__ import unicode_literals

from pyramid.config import Configurator
from pyramid.authorization import ACLAuthorizationPolicy

from billy.models import setup_database
from billy.request import APIRequest
from billy.api.auth import AuthenticationPolicy


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.

    """
    # setup database
    settings = setup_database(global_config, **settings)
    config = Configurator(
        settings=settings,
        request_factory=APIRequest,
        authentication_policy=AuthenticationPolicy(),
        authorization_policy=ACLAuthorizationPolicy(),
        default_permission='view',
    )
    # add basic authentication parsing
    config.add_tween('.api.auth.basic_auth_tween_factory')
    # add access-control-allow-origin header setting
    config.add_tween('.api.allow_origin.allow_origin_tween_factory')
    # provides table entity to json renderers
    config.include('.renderers')
    # provides api views
    config.include('.api')

    config.scan(ignore=b'billy.tests')
    return config.make_wsgi_app()
