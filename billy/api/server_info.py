from __future__ import unicode_literals

from pyramid.view import view_config

from billy.utils.generic import get_git_rev


@view_config(route_name='server_info', 
             request_method='GET', 
             renderer='json')
def server_info(request):
    """Get server info

    """
    # TODO: get some more useful information here, such as the date time
    # of last yield transaction?
    return dict(
        server='Billy - The recurring payment server powered by Balanced',
        revision=get_git_rev(),
    )
