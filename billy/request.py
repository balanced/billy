from __future__ import unicode_literals

from pyramid.request import Request
from pyramid.decorator import reify
from pyramid.path import DottedNameResolver

from billy.api.model_factory import ModelFactory


class APIRequest(Request):
    
    @reify
    def session(self):
        """Session object for database operations
        
        """
        settings = self.registry.settings
        return settings['session']

    @reify
    def processor(self):
        """The payment processor

        """
        settings = self.registry.settings
        resolver = DottedNameResolver()
        processor_factory = settings['billy.processor_factory']
        processor_factory = resolver.maybe_resolve(processor_factory)
        processor = processor_factory()
        return processor

    @reify
    def model_factory(self):
        """The factory for creating data models

        """
        return ModelFactory(self)
