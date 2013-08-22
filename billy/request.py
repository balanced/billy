from pyramid.request import Request
from pyramid.decorator import reify


class APIRequest(Request):
    
    @reify
    def session(self):
        """Session object for database operations
        
        """
        settions = self.registry.settings
        return settions['session']
