from __future__ import unicode_literals

from pyramid.settings import asbool
from pyramid.request import Request
from pyramid.decorator import reify
from pyramid.events import NewResponse
from pyramid.events import NewRequest
from pyramid.events import subscriber

from billy.models.model_factory import ModelFactory
from billy.api.utils import get_processor_factory


class APIRequest(Request):
   
    @reify
    def session(self):
        """Session object for database operations
       
        """
        settings = self.registry.settings
        return settings['session']

    @reify
    def model_factory(self):
        """The factory for creating data models

        """
        settings = self.registry.settings
        model_factory_func = settings.get('model_factory_func')
        if model_factory_func is not None:
            return model_factory_func()
        processor_factory = get_processor_factory(settings)
        return ModelFactory(
            session=self.session,
            processor_factory=processor_factory,
            settings=settings,
        )


@subscriber(NewResponse)
def clean_balanced_processor_key(event):
    """This ensures we won't leave the API key of balanced to the same thread
    (as there is a thread local object in Balanced API), in case of using it
    later by accident, or for security reason.

    """
    import balanced
    balanced.configure(None)


@subscriber(NewRequest)
def clean_db_session(event):
    """Clean up DB session when the request processing is finished
        
    """
    def clean_up(request):
        request.session.remove()

    settings = event.request.registry.settings
    db_session_cleanup = asbool(settings.get('db_session_cleanup', True))
    if db_session_cleanup:
        event.request.add_finished_callback(clean_up)
