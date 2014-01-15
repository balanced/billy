from __future__ import unicode_literals
import functools

from pyramid.view import view_defaults

api_view_defaults = functools.partial(view_defaults, renderer='json')


@api_view_defaults()
class BaseView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request


class IndexView(BaseView):
    pass
   

class EntityView(BaseView):
    pass
