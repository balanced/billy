from __future__ import unicode_literals

from pyramid.request import Request
from pyramid.decorator import reify

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
        processor_factory = get_processor_factory(settings)
        return ModelFactory(
            session=self.session, 
            processor_factory=processor_factory, 
            settings=settings,
        )
