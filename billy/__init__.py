from pyramid.config import Configurator

from billy.models import setup_database
from billy.request import APIRequest


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.

    """
    # setup database
    settings = setup_database(global_config, **settings)
    config = Configurator(
        settings=settings, 
        request_factory=APIRequest, 
    )
    # provides table entity to json renderers
    config.include('.renderers')
    # provides api views
    config.include('.api')

    config.scan()
    return config.make_wsgi_app()
